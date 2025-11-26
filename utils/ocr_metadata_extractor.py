"""
Extractor de metadatos usando OCR (Tesseract) - 100% GRATUITO.
Lee texto de imágenes en PDFs sin costos.
"""

import re
import logging
from typing import Dict, Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)


class OCRMetadataExtractor:
    """Extractor de metadatos usando OCR (Tesseract) - GRATIS."""
    
    @staticmethod
    def extraer_metadatos_de_pdf(pdf_path: str, pagina: int = 0, debug: bool = False) -> Dict:
        """
        Extrae metadatos de una página del PDF usando OCR.
        
        Args:
            pdf_path: Ruta al PDF
            pagina: Número de página (0 = primera)
            debug: Mostrar texto OCR extraído
            
        Returns:
            Diccionario con metadatos extraídos
        """
        try:
            # 1. Convertir página a imagen y extraer texto con OCR
            logger.info(f"📸 Extrayendo texto con OCR de página {pagina+1}...")
            texto_ocr = OCRMetadataExtractor._extraer_texto_ocr(pdf_path, pagina)
            
            if not texto_ocr:
                logger.error("❌ No se pudo extraer texto con OCR")
                return {}
            
            if debug:
                logger.info("="*60)
                logger.info("TEXTO EXTRAÍDO CON OCR:")
                logger.info(texto_ocr[:500])
                logger.info("="*60)
            
            # 2. Buscar metadatos en el texto OCR
            metadatos = OCRMetadataExtractor._parsear_metadatos(texto_ocr, debug)
            
            if metadatos:
                logger.info("✅ Metadatos extraídos con OCR:")
                for key, value in metadatos.items():
                    if value:
                        logger.info(f"  {key}: {value}")
            
            return metadatos
            
        except Exception as e:
            logger.error(f"❌ Error en extracción con OCR: {e}")
            return {}
    
    @staticmethod
    def _extraer_texto_ocr(pdf_path: str, pagina: int = 0) -> Optional[str]:
        """
        Convierte página de PDF a imagen y extrae texto con OCR.
        
        Returns:
            Texto extraído
        """
        try:
            from pdf2image import convert_from_path
            import pytesseract
            
            # Convertir página a imagen (alta resolución para mejor OCR)
            logger.info(f"  Convirtiendo página {pagina+1} a imagen...")
            images = convert_from_path(
                pdf_path, 
                first_page=pagina+1,
                last_page=pagina+1,
                dpi=300  # Alta resolución para OCR
            )
            
            if not images:
                logger.error("  No se pudo convertir página")
                return None
            
            # Extraer texto con OCR (español + inglés)
            logger.info("  Ejecutando OCR...")
            texto = pytesseract.image_to_string(
                images[0], 
                lang='spa+eng',  # Español e inglés
                config='--psm 6'  # Modo: bloque de texto uniforme
            )
            
            logger.info(f"  ✓ OCR completado: {len(texto)} caracteres extraídos")
            
            return texto
            
        except ImportError as e:
            logger.error("❌ Faltan dependencias:")
            logger.error("   pip install pytesseract pdf2image pillow")
            logger.error("   sudo apt-get install tesseract-ocr tesseract-ocr-spa poppler-utils")
            return None
        except Exception as e:
            logger.error(f"  Error en OCR: {e}")
            return None
    
    @staticmethod
    def _parsear_metadatos(texto: str, debug: bool = False) -> Dict:
        """
        Busca metadatos en el texto extraído por OCR.
        
        Args:
            texto: Texto extraído
            debug: Mostrar coincidencias encontradas
            
        Returns:
            Diccionario con metadatos
        """
        metadatos = {}
        
        # Limpiar texto (OCR a veces añade espacios raros)
        texto_limpio = texto.replace('\n', ' ').replace('  ', ' ')
        
        # 1. Código centro (6 dígitos)
        patrones_centro = [
            r'[Cc][óo]digo\s+centro[:\s]+(\d{6})',
            r'[Cc][óo]digo\s+centro[:\s]*(\d{6})',
            r'Centro[:\s]+(\d{6})',
            r'C[óo]d\.\s*Centro[:\s]+(\d{6})',
        ]
        
        for patron in patrones_centro:
            match = re.search(patron, texto, re.IGNORECASE)
            if match:
                metadatos['codigo_centro'] = match.group(1)
                if debug:
                    logger.info(f"  ✓ Código centro: {match.group(1)}")
                break
        
        # 2. Nombre centro
        patrones_nombre = [
            r'ID/Nombre[:\s]+(.+?)\s+C[óo]digo',
            r'ID/Nombre[:\s]+(.+?)(?:\n|$)',
            r'Nombre[:\s]+(.+?)(?:\n|C[óo]digo)',
        ]
        
        for patron in patrones_nombre:
            match = re.search(patron, texto, re.IGNORECASE)
            if match:
                nombre = match.group(1).strip()
                if nombre and not re.match(r'^\d+$', nombre):
                    metadatos['nombre_centro'] = nombre
                    if debug:
                        logger.info(f"  ✓ Nombre centro: {nombre}")
                    break
        
        # 3. Categoría (1-5)
        patrones_categoria = [
            r'Categor[íi]a[:\s]+(\d)',
            r'Cat[:\.\s]+(\d)',
            r'CATEGORIA[:\s]+(\d)',
        ]
        
        for patron in patrones_categoria:
            match = re.search(patron, texto, re.IGNORECASE)
            if match:
                cat = int(match.group(1))
                if 1 <= cat <= 5:
                    metadatos['categoria'] = cat
                    if debug:
                        logger.info(f"  ✓ Categoría: {cat}")
                    break
        
        # 4. Tipo de monitoreo
        if 'POST' in texto.upper() or 'POSTANAER' in texto.upper():
            metadatos['tipo_monitoreo'] = 'INFA-POSTANAEROBICA'
        elif 'INFA' in texto.upper():
            metadatos['tipo_monitoreo'] = 'INFA'
        elif 'CPS' in texto.upper():
            metadatos['tipo_monitoreo'] = 'CPS'
        
        if debug and metadatos.get('tipo_monitoreo'):
            logger.info(f"  ✓ Tipo monitoreo: {metadatos['tipo_monitoreo']}")
        
        # 5. Fecha muestreo
        patrones_fecha_muestreo = [
            r'Fecha\s+Inicio[/\s]*Fin[:\s]+(\d{2}[/\-]\d{2}[/\-]\d{4})',
            r'Fecha\s+[Mm]uestreo[:\s]+(\d{2}[/\-]\d{2}[/\-]\d{4})',
        ]
        
        for patron in patrones_fecha_muestreo:
            match = re.search(patron, texto, re.IGNORECASE)
            if match:
                fecha = OCRMetadataExtractor._normalizar_fecha(match.group(1))
                if fecha:
                    metadatos['fecha_muestreo'] = fecha
                    if debug:
                        logger.info(f"  ✓ Fecha muestreo: {fecha}")
                    break
        
        # 6. Fecha ingreso
        patrones_fecha_ingreso = [
            r'Fecha\s+ingreso\s+laboratorio[:\s]+(\d{2}[/\-]\d{2}[/\-]\d{4})',
            r'ingreso\s+laboratorio[:\s]+(\d{2}[/\-]\d{2}[/\-]\d{4})',
        ]
        
        for patron in patrones_fecha_ingreso:
            match = re.search(patron, texto, re.IGNORECASE)
            if match:
                fecha = OCRMetadataExtractor._normalizar_fecha(match.group(1))
                if fecha:
                    metadatos['fecha_ingreso'] = fecha
                    if debug:
                        logger.info(f"  ✓ Fecha ingreso: {fecha}")
                    break
        
        # 7. Responsable
        patrones_responsable = [
            r'Responsable[:\s]+([A-Za-zÁ-ú\s]+?)(?:\n|Fecha)',
            r'Responsable\s+Terreno[:\s]+([A-Za-zÁ-ú\s]+?)(?:\n|$)',
        ]
        
        for patron in patrones_responsable:
            match = re.search(patron, texto, re.IGNORECASE)
            if match:
                responsable = match.group(1).strip()
                if responsable:
                    metadatos['responsable'] = responsable
                    if debug:
                        logger.info(f"  ✓ Responsable: {responsable}")
                    break
        
        return metadatos
    
    @staticmethod
    def _normalizar_fecha(fecha_str: str) -> Optional[str]:
        """Convierte DD/MM/YYYY a YYYY-MM-DD."""
        try:
            # Limpiar caracteres extraños del OCR
            fecha_str = fecha_str.replace(' ', '').replace(',', '').replace('.', '/')
            
            partes = re.split(r'[/-]', fecha_str)
            if len(partes) == 3:
                dia, mes, año = partes
                dia = dia.zfill(2)
                mes = mes.zfill(2)
                
                # Validar
                if 1 <= int(dia) <= 31 and 1 <= int(mes) <= 12 and 1900 <= int(año) <= 2100:
                    return f"{año}-{mes}-{dia}"
        except:
            pass
        
        return None


def test_ocr_extractor(pdf_path: str):
    """Función de prueba."""
    import logging
    logging.basicConfig(
        level=logging.INFO, 
        format='[%(levelname)s] %(message)s'
    )
    
    print("="*60)
    print(f"🔍 Probando OCR en: {Path(pdf_path).name}")
    print("="*60)
    
    extractor = OCRMetadataExtractor()
    metadatos = extractor.extraer_metadatos_de_pdf(pdf_path, pagina=0, debug=True)
    
    print("\n" + "="*60)
    print("📋 RESULTADO:")
    print("="*60)
    
    if metadatos:
        for key, value in metadatos.items():
            print(f"  {key}: {value}")
    else:
        print("  ❌ No se extrajeron metadatos")
    
    print("="*60)


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        test_ocr_extractor(sys.argv[1])
    else:
        print("Uso: python ocr_metadata_extractor.py <archivo.pdf>")
