"""
Extractor unificado de metadatos con OCR automático.
Combina: metadata_extractor.py + ocr_metadata_extractor.py + normalizadores.py
"""

import re
import logging
from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime

from config.patterns import METADATA_PATTERNS, DEFAULT_VALUES

logger = logging.getLogger(__name__)


class MetadataExtractor:
    """
    Extractor unificado de metadatos con OCR automático.
    
    Características:
    - Extracción desde texto normal
    - OCR automático si página 1 está vacía
    - Normalización automática de valores
    - Múltiples patrones por campo
    """
    
    @classmethod
    def extract_all(cls, pdf_path: str, textos_por_pagina: List[str], 
                    debug: bool = False) -> Dict:
        """
        Extrae TODOS los metadatos del PDF.
        
        Args:
            pdf_path: Ruta al PDF
            textos_por_pagina: Textos extraídos por PDFReader
            debug: Modo debug
        
        Returns:
            Diccionario con metadatos
        """
        metadatos = cls._init_metadata(pdf_path)
        
        # 1. OT desde nombre archivo (prioritario y más confiable)
        metadatos['codigo_ot'] = cls._extract_ot_from_filename(pdf_path)
        
        # 2. Si página 1 vacía → OCR
        if not textos_por_pagina[0] or len(textos_por_pagina[0].strip()) < 50:
            logger.info("🔍 Página 1 vacía, activando OCR...")
            metadatos_ocr = cls._extract_with_ocr(pdf_path, debug)
            
            # Actualizar solo campos que OCR encontró
            for key, value in metadatos_ocr.items():
                if value:
                    metadatos[key] = value
            
            if metadatos_ocr:
                logger.info("✅ Metadatos obtenidos con OCR")
        
        # 3. Extraer desde texto normal (campos que faltan)
        texto_completo = "\n".join(textos_por_pagina)
        
        for campo in ['codigo_centro', 'nombre_centro', 'categoria', 
                      'tipo_monitoreo', 'fecha_ingreso', 'fecha_muestreo', 'responsable']:
            
            if not metadatos.get(campo) and campo in METADATA_PATTERNS:
                valor = cls._search_with_patterns(
                    texto_completo, 
                    METADATA_PATTERNS[campo]
                )
                
                if valor:
                    metadatos[campo] = valor
                    if debug:
                        logger.debug(f"✓ {campo}: {valor}")
        
        # 4. Normalizar valores
        cls._normalize_metadata(metadatos)
        
        # 5. Detectar condición desde texto si no está
        if not metadatos.get('condicion_centro'):
            metadatos['condicion_centro'] = cls._detect_condition(texto_completo)
        
        # 6. Log final
        if debug:
            cls._log_metadata(metadatos)
        
        return metadatos
    
    @staticmethod
    def _init_metadata(pdf_path: str) -> Dict:
        """Inicializa estructura de metadatos."""
        return {
            'nombre_archivo': Path(pdf_path).name,
            'codigo_ot': None,
            'codigo_centro': None,
            'nombre_centro': None,
            'categoria': None,
            'tipo_monitoreo': None,
            'fecha_ingreso': None,
            'fecha_muestreo': None,
            'condicion_centro': None,
            'responsable': None,
        }
    
    @staticmethod
    def _extract_ot_from_filename(pdf_path: str) -> Optional[str]:
        """Extrae código OT del nombre del archivo."""
        nombre = Path(pdf_path).stem
        
        for patron in METADATA_PATTERNS['OT']:
            match = re.search(patron, nombre, re.IGNORECASE)
            if match:
                ot = match.group(1)
                logger.debug(f"OT extraído del nombre: {ot}")
                return ot
        
        logger.warning("No se pudo extraer OT del nombre del archivo")
        return None
    
    @staticmethod
    def _search_with_patterns(texto: str, patrones: List[str]) -> Optional[str]:
        """Busca usando múltiples patrones en orden de prioridad."""
        for patron in patrones:
            try:
                match = re.search(patron, texto, re.IGNORECASE | re.MULTILINE)
                if match:
                    valor = match.group(1).strip()
                    logger.debug(f"Match: {patron[:30]}... → {valor}")
                    return valor
            except Exception as e:
                logger.debug(f"Error con patrón {patron}: {e}")
        
        return None
    
    @classmethod
    def _extract_with_ocr(cls, pdf_path: str, debug: bool) -> Dict:
        """
        Extrae metadatos usando OCR (Tesseract).
        
        Requiere:
        - pytesseract
        - pdf2image
        - tesseract-ocr instalado en sistema
        """
        try:
            from pdf2image import convert_from_path
            import pytesseract
            
            # Convertir solo página 1 a imagen (alta resolución)
            logger.info("  📸 Convirtiendo página 1 a imagen...")
            images = convert_from_path(
                pdf_path, 
                first_page=1, 
                last_page=1, 
                dpi=300
            )
            
            if not images:
                logger.error("  No se pudo convertir página")
                return {}
            
            # Ejecutar OCR (español + inglés)
            logger.info("  🔍 Ejecutando OCR...")
            texto_ocr = pytesseract.image_to_string(
                images[0], 
                lang='spa+eng',
                config='--psm 6'
            )
            
            logger.info(f"  ✅ OCR completado: {len(texto_ocr)} caracteres")
            
            if debug:
                logger.debug("--- TEXTO OCR (primeros 500 chars) ---")
                logger.debug(texto_ocr[:500])
                logger.debug("-" * 40)
            
            # Parsear metadatos del texto OCR
            return cls._parse_ocr_text(texto_ocr, debug)
            
        except ImportError:
            logger.warning("⚠️ OCR no disponible")
            logger.info("   Instalar: pip install pytesseract pdf2image")
            logger.info("   Sistema: sudo apt-get install tesseract-ocr tesseract-ocr-spa poppler-utils")
            return {}
        except Exception as e:
            logger.error(f"Error en OCR: {e}")
            return {}
    
    @classmethod
    def _parse_ocr_text(cls, texto: str, debug: bool) -> Dict:
        """Parsea metadatos del texto extraído por OCR."""
        resultado = {}
        
        # Código centro (6 dígitos)
        match = re.search(r'[Cc][óo]digo\s+centro[:\s]*(\d{6})', texto, re.I)
        if match:
            resultado['codigo_centro'] = match.group(1)
            if debug:
                logger.debug(f"  ✓ OCR - Código centro: {match.group(1)}")
        
        # Nombre centro
        match = re.search(r'ID/Nombre[:\s]+(.+?)(?:\s+C[óo]digo|\n)', texto, re.I)
        if match:
            nombre = match.group(1).strip()
            if nombre and not re.match(r'^\d+$', nombre):
                resultado['nombre_centro'] = nombre
                if debug:
                    logger.debug(f"  ✓ OCR - Nombre: {nombre}")
        
        # Categoría
        match = re.search(r'Categor[íi]a[:\s]+(\d)', texto, re.I)
        if match:
            cat = int(match.group(1))
            if 1 <= cat <= 5:
                resultado['categoria'] = cat
                if debug:
                    logger.debug(f"  ✓ OCR - Categoría: {cat}")
        
        # Tipo monitoreo
        if 'POST' in texto.upper() or 'POSTANAER' in texto.upper():
            resultado['tipo_monitoreo'] = 'INFA-POSTANAEROBICA'
        elif 'INFA' in texto.upper():
            resultado['tipo_monitoreo'] = 'INFA'
        elif 'CPS' in texto.upper():
            resultado['tipo_monitoreo'] = 'CPS'
        
        if debug and resultado.get('tipo_monitoreo'):
            logger.debug(f"  ✓ OCR - Tipo: {resultado['tipo_monitoreo']}")
        
        # Fecha muestreo
        match = re.search(r'Fecha\s+Inicio[:/\s]*Fin[:\s]*(\d{2}[/-]\d{2}[/-]\d{4})', texto, re.I)
        if match:
            fecha = cls._normalize_date(match.group(1))
            if fecha:
                resultado['fecha_muestreo'] = fecha
                if debug:
                    logger.debug(f"  ✓ OCR - Fecha muestreo: {fecha}")
        
        # Fecha ingreso laboratorio
        match = re.search(r'[Ii]ngreso\s+[Ll]aboratorio[:\s]*(\d{2}[/-]\d{2}[/-]\d{4})', texto, re.I)
        if match:
            fecha = cls._normalize_date(match.group(1))
            if fecha:
                resultado['fecha_ingreso'] = fecha
                if debug:
                    logger.debug(f"  ✓ OCR - Fecha ingreso: {fecha}")
        
        # Responsable
        match = re.search(r'Responsable[:\s]+([A-Za-zÁ-ú\s/]+?)(?:\n|Fecha)', texto, re.I)
        if match:
            responsable = match.group(1).strip()
            if responsable:
                resultado['responsable'] = responsable
                if debug:
                    logger.debug(f"  ✓ OCR - Responsable: {responsable}")
        
        return resultado
    
    @staticmethod
    def _normalize_date(fecha_str: str) -> Optional[str]:
        """
        Normaliza fecha a formato YYYY-MM-DD.
        
        Acepta: DD/MM/YYYY, DD-MM-YYYY
        """
        try:
            # Limpiar caracteres extraños del OCR
            fecha_str = fecha_str.replace(' ', '').replace(',', '')
            
            partes = re.split(r'[/-]', fecha_str)
            if len(partes) == 3:
                dia, mes, año = partes
                dia = dia.zfill(2)
                mes = mes.zfill(2)
                
                # Validar rangos
                if 1 <= int(dia) <= 31 and 1 <= int(mes) <= 12 and 1900 <= int(año) <= 2100:
                    return f"{año}-{mes}-{dia}"
        except:
            pass
        
        logger.debug(f"Fecha inválida: {fecha_str}")
        return None
    
    @staticmethod
    def _normalize_metadata(metadatos: Dict):
        """Normaliza valores de metadatos in-place."""
        # Tipo monitoreo
        if metadatos.get('tipo_monitoreo'):
            tipo = metadatos['tipo_monitoreo'].upper()
            if 'POST' in tipo:
                metadatos['tipo_monitoreo'] = 'INFA-POSTANAEROBICA'
            elif 'INFA' in tipo:
                metadatos['tipo_monitoreo'] = 'INFA'
            elif 'CPS' in tipo:
                metadatos['tipo_monitoreo'] = 'CPS'
        
        # Condición centro
        if metadatos.get('condicion_centro'):
            cond = metadatos['condicion_centro'].upper()
            if 'ANAER' in cond:
                metadatos['condicion_centro'] = 'ANAEROBICO'
            elif 'AER' in cond:
                metadatos['condicion_centro'] = 'AEROBICO'
        
        # Categoría a entero
        if metadatos.get('categoria') and isinstance(metadatos['categoria'], str):
            try:
                metadatos['categoria'] = int(metadatos['categoria'])
            except:
                pass
    
    @staticmethod
    def _detect_condition(texto: str) -> Optional[str]:
        """Detecta condición del centro desde el texto."""
        texto_upper = texto.upper()
        
        if 'ANAEROBICO' in texto_upper or 'ANAEROB' in texto_upper:
            return 'ANAEROBICO'
        elif 'AEROBICO' in texto_upper or 'AEROB' in texto_upper:
            return 'AEROBICO'
        
        return None
    
    @staticmethod
    def _log_metadata(metadatos: Dict):
        """Log de metadatos extraídos."""
        logger.info("📋 Metadatos extraídos:")
        
        campos_orden = [
            'codigo_ot', 'codigo_centro', 'nombre_centro', 'categoria',
            'tipo_monitoreo', 'condicion_centro', 'fecha_muestreo', 
            'fecha_ingreso', 'responsable'
        ]
        
        for campo in campos_orden:
            valor = metadatos.get(campo)
            if valor:
                logger.info(f"  {campo}: {valor}")


def test_metadata_extractor(pdf_path: str):
    """Función de prueba."""
    from core.pdf_reader import PDFReader
    
    print("=" * 60)
    print(f"Probando MetadataExtractor: {Path(pdf_path).name}")
    print("=" * 60)
    
    # Leer PDF
    reader = PDFReader(pdf_path)
    textos = reader.extract_all_pages_text()
    
    # Extraer metadatos
    print("\n📋 Extrayendo metadatos...")
    metadatos = MetadataExtractor.extract_all(pdf_path, textos, debug=True)
    
    print("\n" + "=" * 60)
    print("✅ Extracción completada")
    print("=" * 60)


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        test_metadata_extractor(sys.argv[1])
    else:
        print("Uso: python metadata.py <archivo.pdf>")
