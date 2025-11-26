"""
Extractor robusto de metadatos con multi-patrón y validación.
Versión FINAL: Busca metadatos en todas las páginas + OCR automático.
"""

import re
import logging
from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime
import pdfplumber

from config.extractor_config import (
    METADATA_PATTERNS,
    METADATOS_OBLIGATORIOS,
    RANGOS_VALIDACION
)

logger = logging.getLogger(__name__)


class MetadataExtractor:
    """Extractor de metadatos con búsqueda multi-patrón y OCR."""
    
    @classmethod
    def extraer_todos(cls, pdf_path: str, debug: bool = False) -> Dict:
        """
        Extrae TODOS los metadatos del PDF.
        Usa OCR automáticamente si las páginas están vacías.
        """
        metadatos = cls._inicializar_metadatos(pdf_path)
        
        try:
            # 1. Extraer OT del nombre del archivo (prioritario)
            metadatos['codigo_ot'] = cls._extraer_ot_from_filename(pdf_path)
            
            # 2. Extraer texto de TODAS las páginas
            textos_por_pagina = cls._extraer_todas_las_paginas(pdf_path)
            
            # 3. Si página 1 está vacía, usar OCR
            usar_ocr = False
            if not textos_por_pagina[0] or len(textos_por_pagina[0].strip()) < 50:
                logger.info("🔍 Página 1 vacía, intentando OCR...")
                metadatos_ocr = cls._extraer_con_ocr(pdf_path, debug)
                
                if metadatos_ocr:
                    # Priorizar metadatos OCR
                    for key, value in metadatos_ocr.items():
                        if value:
                            metadatos[key] = value
                            usar_ocr = True
                    
                    logger.info("✅ Metadatos extraídos con OCR")
            
            if debug:
                logger.info("=" * 60)
                for i, texto in enumerate(textos_por_pagina[:3], 1):
                    logger.info(f"PÁGINA {i} (primeros 500 chars):")
                    logger.info(texto[:500] if texto else "[VACÍA]")
                    logger.info("-" * 60)
                logger.info("=" * 60)
            
            # Texto completo para búsquedas generales
            texto_completo = "\n".join(textos_por_pagina)
            
            # 4. Buscar OT en el texto (si no se encontró en filename)
            if not metadatos['codigo_ot']:
                metadatos['codigo_ot'] = cls._buscar_con_patrones(
                    texto_completo, METADATA_PATTERNS['OT']
                )
            
            # 5. Extraer metadatos SOLO si no vinieron del OCR
            if not usar_ocr:
                logger.info("📄 Extrayendo metadatos de texto...")
                
                metadatos['codigo_centro'] = cls._extraer_en_todas_paginas(
                    textos_por_pagina, 'codigo_centro', debug
                )
                
                metadatos['categoria'] = cls._extraer_categoria_todas_paginas(
                    textos_por_pagina, debug
                )
                
                metadatos['tipo_monitoreo'] = cls._extraer_tipo_monitoreo_todas_paginas(
                    textos_por_pagina, debug
                )
                
                metadatos['fecha_ingreso'] = cls._extraer_fecha_ingreso_todas_paginas(
                    textos_por_pagina, debug
                )
                
                metadatos['fecha_muestreo'] = cls._extraer_fecha_muestreo_todas_paginas(
                    textos_por_pagina, debug
                )
                
                metadatos['nombre_centro'] = cls._extraer_nombre_centro_todas_paginas(
                    textos_por_pagina
                )
            else:
                logger.info("✓ Usando metadatos del OCR (página 1 escaneada)")
            
            # 6. Extraer condición del centro (siempre buscar)
            if not metadatos.get('condicion_centro'):
                metadatos['condicion_centro'] = cls._extraer_condicion_centro(
                    pdf_path, texto_completo
                )
            
            # 7. Validar metadatos críticos
            cls._validar_metadatos(metadatos, pdf_path)
            
            # 8. Log de lo extraído
            cls._log_metadatos(metadatos)
            
            return metadatos
            
        except Exception as e:
            logger.error(f"Error extrayendo metadatos de {Path(pdf_path).name}: {e}")
            return metadatos
    
    @staticmethod
    def _inicializar_metadatos(pdf_path: str) -> Dict:
        """Inicializa estructura de metadatos."""
        return {
            'nombre_archivo': Path(pdf_path).name,
            'codigo_ot': None,
            'codigo_centro': None,
            'categoria': None,
            'tipo_monitoreo': None,
            'fecha_ingreso': None,
            'fecha_muestreo': None,
            'condicion_centro': None,
            'nombre_centro': None,
            'responsable': None,
            'region': None,
        }
    
    @staticmethod
    def _extraer_ot_from_filename(pdf_path: str) -> Optional[str]:
        """Extrae OT del nombre del archivo."""
        nombre = Path(pdf_path).stem
        
        for patron in METADATA_PATTERNS['OT']:
            match = re.search(patron, nombre, re.IGNORECASE)
            if match:
                ot = match.group(1)
                logger.debug(f"OT encontrado en filename: {ot}")
                return ot
        
        return None
    
    @staticmethod
    def _extraer_todas_las_paginas(pdf_path: str) -> List[str]:
        """
        Extrae texto de TODAS las páginas con múltiples métodos.
        """
        # Importar extractor multi-método
        try:
            from utils.pdf_text_extractor import PDFTextExtractor
            return PDFTextExtractor.extraer_todas_paginas(pdf_path, debug=False)
        except ImportError:
            # Fallback a pdfplumber solo
            textos = []
            try:
                with pdfplumber.open(pdf_path) as pdf:
                    for page in pdf.pages:
                        texto = page.extract_text()
                        textos.append(texto if texto else "")
            except Exception as e:
                logger.error(f"Error extrayendo páginas: {e}")
            
            return textos
    
    @staticmethod
    def _buscar_con_patrones(texto: str, patrones: List[str]) -> Optional[str]:
        """Busca usando múltiples patrones en orden de prioridad."""
        for patron in patrones:
            try:
                match = re.search(patron, texto, re.IGNORECASE | re.MULTILINE)
                if match:
                    valor = match.group(1).strip()
                    logger.debug(f"Match con patrón: {patron[:30]}... -> {valor}")
                    return valor
            except Exception as e:
                logger.debug(f"Error con patrón {patron}: {e}")
                continue
        
        return None
    
    @classmethod
    def _extraer_en_todas_paginas(cls, textos: List[str], campo: str, 
                                   debug: bool = False) -> Optional[str]:
        """Busca un campo en TODAS las páginas hasta encontrarlo."""
        if campo not in METADATA_PATTERNS:
            return None
        
        patrones = METADATA_PATTERNS[campo]
        
        # Buscar en cada página
        for num_pag, texto in enumerate(textos, 1):
            if not texto:
                continue
            
            for patron in patrones:
                match = re.search(patron, texto, re.IGNORECASE | re.MULTILINE)
                if match:
                    valor = match.group(1).strip()
                    if debug:
                        logger.info(f"✓ {campo} encontrado en página {num_pag}: {valor}")
                    return valor
        
        if debug:
            logger.warning(f"⚠️ {campo} NO encontrado en ninguna página")
        
        return None
    
    @classmethod
    def _extraer_categoria_todas_paginas(cls, textos: List[str], 
                                         debug: bool = False) -> Optional[int]:
        """Extrae categoría buscando en todas las páginas."""
        patrones = [
            r'Categor[íi]a[:\s]+(\d)',
            r'[Cc]at[:\.\s]+(\d)',
            r'CATEGORIA[:\s]+(\d)',
        ]
        
        for num_pag, texto in enumerate(textos, 1):
            if not texto:
                continue
            
            for patron in patrones:
                match = re.search(patron, texto, re.IGNORECASE | re.MULTILINE)
                if match:
                    cat = int(match.group(1))
                    if 1 <= cat <= 5:
                        if debug:
                            logger.info(f"✓ Categoría encontrada en página {num_pag}: {cat}")
                        return cat
        
        if debug:
            logger.warning("⚠️ Categoría NO encontrada")
        
        return None
    
    @classmethod
    def _extraer_tipo_monitoreo_todas_paginas(cls, textos: List[str],
                                               debug: bool = False) -> Optional[str]:
        """Extrae tipo de monitoreo buscando en todas las páginas."""
        patrones = [
            r'Tipo\s+de\s+[Mm]onitoreo[:\s]+(.+?)(?:\n|$)',
            r'[Mm]onitoreo\s+interno[:\s]+(.+?)(?:\n|$)',
            r'[Mm]onitoreo[:\s]+(.+?)(?:\n|$)',
            r'(INFA[- ]?POST[- ]?ANAER[ÓO]BIC[OA])',
            r'(POST[- ]?ANAER[ÓO]BIC[OA])',
            r'\b(INFA)\b',
            r'\b(CPS)\b',
        ]
        
        for num_pag, texto in enumerate(textos, 1):
            if not texto:
                continue
            
            for patron in patrones:
                match = re.search(patron, texto, re.IGNORECASE | re.MULTILINE)
                if match:
                    valor = match.group(1).strip()
                    tipo = cls._normalizar_tipo_monitoreo(valor)
                    if debug:
                        logger.info(f"✓ Tipo monitoreo (pág. {num_pag}): '{valor}' -> '{tipo}'")
                    return tipo
        
        if debug:
            logger.warning("⚠️ Tipo de monitoreo NO encontrado")
        
        return None
    
    @staticmethod
    def _normalizar_tipo_monitoreo(valor: Optional[str]) -> Optional[str]:
        """Normaliza tipo de monitoreo."""
        if not valor:
            return None
        
        valor_upper = valor.upper()
        
        if 'POST' in valor_upper or 'POSTANAER' in valor_upper:
            return 'INFA-POSTANAEROBICA'
        elif 'INFA' in valor_upper:
            return 'INFA'
        elif 'CPS' in valor_upper:
            return 'CPS'
        
        return valor.strip()
    
    @classmethod
    def _extraer_fecha_ingreso_todas_paginas(cls, textos: List[str],
                                              debug: bool = False) -> Optional[str]:
        """Extrae fecha de ingreso buscando en todas las páginas."""
        patrones = [
            r'Fecha\s+ingreso\s+laboratorio[:\s]+(\d{2}[/\-]\d{2}[/\-]\d{4})',
            r'Fecha\s+ingreso[:\s]+(\d{2}[/\-]\d{2}[/\-]\d{4})',
            r'[Ii]ngreso[:\s]+laboratorio[:\s]+(\d{2}[/\-]\d{2}[/\-]\d{4})',
        ]
        
        for num_pag, texto in enumerate(textos, 1):
            if not texto:
                continue
            
            for patron in patrones:
                match = re.search(patron, texto, re.IGNORECASE | re.MULTILINE)
                if match:
                    fecha = cls._normalizar_fecha(match.group(1))
                    if fecha and debug:
                        logger.info(f"✓ Fecha ingreso (pág. {num_pag}): {fecha}")
                    return fecha
        
        if debug:
            logger.warning("⚠️ Fecha ingreso NO encontrada")
        
        return None
    
    @classmethod
    def _extraer_fecha_muestreo_todas_paginas(cls, textos: List[str],
                                               debug: bool = False) -> Optional[str]:
        """Extrae fecha de muestreo buscando en todas las páginas."""
        patrones = [
            r'Fecha\s+Inicio[/\s]*Fin[:\s]+(\d{2}[/\-]\d{2}[/\-]\d{4})',
            r'Fecha\s+[Mm]uestreo[:\s]+(\d{2}[/\-]\d{2}[/\-]\d{4})',
            r'Fecha\s+[Ii]nicio[:\s]+(\d{2}[/\-]\d{2}[/\-]\d{4})',
        ]
        
        for num_pag, texto in enumerate(textos, 1):
            if not texto:
                continue
            
            for patron in patrones:
                match = re.search(patron, texto, re.IGNORECASE | re.MULTILINE)
                if match:
                    fecha = cls._normalizar_fecha(match.group(1))
                    if fecha and debug:
                        logger.info(f"✓ Fecha muestreo (pág. {num_pag}): {fecha}")
                    return fecha
        
        if debug:
            logger.warning("⚠️ Fecha muestreo NO encontrada")
        
        return None
    
    @staticmethod
    def _normalizar_fecha(fecha_str: Optional[str]) -> Optional[str]:
        """Convierte fecha a formato YYYY-MM-DD."""
        if not fecha_str:
            return None
        
        try:
            partes = re.split(r'[/-]', fecha_str)
            if len(partes) == 3:
                dia, mes, año = partes
                if 1 <= int(dia) <= 31 and 1 <= int(mes) <= 12 and 1900 <= int(año) <= 2100:
                    return f"{año}-{mes.zfill(2)}-{dia.zfill(2)}"
        except:
            pass
        
        logger.warning(f"Fecha inválida: {fecha_str}")
        return None
    
    @classmethod
    def _extraer_condicion_centro(cls, pdf_path: str, texto: str) -> Optional[str]:
        """Extrae condición del centro."""
        condicion = cls._buscar_con_patrones(texto, METADATA_PATTERNS['CONDICION_CENTRO'])
        
        if condicion:
            return cls._normalizar_condicion(condicion)
        
        # Buscar en tablas
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    tables = page.extract_tables()
                    for table in tables:
                        for row in table:
                            for cell in row:
                                if cell and isinstance(cell, str):
                                    cell_upper = cell.upper()
                                    if 'ANAEROBIC' in cell_upper or 'ANAEROB' in cell_upper:
                                        return 'ANAEROBICO'
                                    elif 'AEROBIC' in cell_upper or 'AEROB' in cell_upper:
                                        return 'AEROBICO'
        except Exception as e:
            logger.debug(f"Error buscando condición en tablas: {e}")
        
        logger.warning("⚠️ No se pudo extraer condición del centro")
        return None
    
    @staticmethod
    def _normalizar_condicion(valor: Optional[str]) -> Optional[str]:
        """Normaliza condición a AEROBICO o ANAEROBICO."""
        if not valor:
            return None
        
        valor_upper = valor.upper()
        
        if 'ANAER' in valor_upper:
            return 'ANAEROBICO'
        elif 'AER' in valor_upper:
            return 'AEROBICO'
        
        return None
    
    @classmethod
    def _extraer_nombre_centro_todas_paginas(cls, textos: List[str]) -> Optional[str]:
        """Extrae nombre del centro buscando en todas las páginas."""
        patrones = [
            r'ID/Nombre[:\s]+(.+?)(?:\n|Código|Código)',
            r'Nombre\s+Centro[:\s]+(.+?)(?:\n|$)',
            r'Centro[:\s]+([A-Za-zÀ-ÿ\s]+\d*)',
        ]
        
        for texto in textos:
            if not texto:
                continue
            
            for patron in patrones:
                match = re.search(patron, texto, re.IGNORECASE | re.MULTILINE)
                if match:
                    nombre = match.group(1).strip()
                    if not re.match(r'^\d+$', nombre):  # No solo números
                        return nombre
        
        return None
    
    @staticmethod
    def _validar_metadatos(metadatos: Dict, pdf_path: str):
        """Valida que existan metadatos críticos."""
        faltantes = []
        
        for campo in METADATOS_OBLIGATORIOS:
            if not metadatos.get(campo):
                faltantes.append(campo)
        
        if faltantes:
            logger.warning(
                f"⚠️ {Path(pdf_path).name} - Metadatos faltantes: {', '.join(faltantes)}"
            )
    
    @staticmethod
    def _log_metadatos(metadatos: Dict):
        """Log de metadatos extraídos."""
        logger.info("📋 Metadatos extraídos:")
        logger.info(f"  OT: {metadatos.get('codigo_ot')}")
        logger.info(f"  Centro: {metadatos.get('codigo_centro')}")
        logger.info(f"  Nombre: {metadatos.get('nombre_centro')}")
        logger.info(f"  Categoría: {metadatos.get('categoria')}")
        logger.info(f"  Tipo: {metadatos.get('tipo_monitoreo')}")
        logger.info(f"  Condición: {metadatos.get('condicion_centro')}")
        logger.info(f"  Fecha muestreo: {metadatos.get('fecha_muestreo')}")
        logger.info(f"  Fecha ingreso: {metadatos.get('fecha_ingreso')}")
    
    @classmethod
    def _extraer_con_ocr(cls, pdf_path: str, debug: bool = False) -> Dict:
        """
        Extrae metadatos usando OCR cuando el texto no es extraíble.
        """
        try:
            from utils.ocr_metadata_extractor import OCRMetadataExtractor
            
            extractor = OCRMetadataExtractor()
            metadatos_ocr = extractor.extraer_metadatos_de_pdf(
                pdf_path, 
                pagina=0, 
                debug=debug
            )
            
            return metadatos_ocr
            
        except ImportError:
            logger.warning("⚠️ OCR no disponible (falta instalar pytesseract)")
            logger.info("   Instalar: pip install pytesseract pdf2image pillow")
            logger.info("   Sistema: sudo apt-get install tesseract-ocr tesseract-ocr-spa poppler-utils")
            return {}
        except Exception as e:
            logger.error(f"Error en OCR: {e}")
            return {}
