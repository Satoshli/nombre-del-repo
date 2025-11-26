"""
Extractor de texto de PDFs con múltiples estrategias.
Fallback automático si pdfplumber falla.
"""

import logging
from typing import List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class PDFTextExtractor:
    """Extractor robusto con múltiples métodos."""
    
    @staticmethod
    def extraer_todas_paginas(pdf_path: str, debug: bool = False) -> List[str]:
        """
        Extrae texto de TODAS las páginas usando múltiples métodos.
        
        Returns:
            Lista de strings, uno por página
        """
        # Intentar método 1: pdfplumber
        textos = PDFTextExtractor._extraer_con_pdfplumber(pdf_path, debug)
        
        # Si alguna página está vacía, intentar PyPDF2
        if any(not texto or len(texto.strip()) < 50 for texto in textos):
            if debug:
                logger.info("🔄 pdfplumber no extrajo todo, probando PyPDF2...")
            textos_pypdf = PDFTextExtractor._extraer_con_pypdf2(pdf_path, debug)
            
            # Combinar: usar PyPDF2 donde pdfplumber falló
            for i in range(len(textos)):
                if not textos[i] or len(textos[i].strip()) < 50:
                    if i < len(textos_pypdf) and textos_pypdf[i]:
                        textos[i] = textos_pypdf[i]
                        if debug:
                            logger.info(f"✓ Página {i+1} extraída con PyPDF2")
        
        # Si aún hay páginas vacías, intentar extraer tablas
        for i, texto in enumerate(textos):
            if not texto or len(texto.strip()) < 50:
                if debug:
                    logger.info(f"🔄 Intentando extraer tabla de página {i+1}...")
                texto_tabla = PDFTextExtractor._extraer_tabla_pagina(pdf_path, i, debug)
                if texto_tabla:
                    textos[i] = texto_tabla
        
        return textos
    
    @staticmethod
    def _extraer_con_pdfplumber(pdf_path: str, debug: bool = False) -> List[str]:
        """Extrae con pdfplumber."""
        textos = []
        try:
            import pdfplumber
            
            with pdfplumber.open(pdf_path) as pdf:
                for i, page in enumerate(pdf.pages):
                    texto = page.extract_text()
                    textos.append(texto if texto else "")
                    
                    if debug and not texto:
                        logger.warning(f"⚠️ pdfplumber: página {i+1} vacía")
            
            return textos
            
        except Exception as e:
            logger.error(f"Error con pdfplumber: {e}")
            return []
    
    @staticmethod
    def _extraer_con_pypdf2(pdf_path: str, debug: bool = False) -> List[str]:
        """Extrae con PyPDF2 (método alternativo)."""
        textos = []
        try:
            from PyPDF2 import PdfReader
            
            reader = PdfReader(pdf_path)
            
            for i, page in enumerate(reader.pages):
                try:
                    texto = page.extract_text()
                    textos.append(texto if texto else "")
                    
                    if debug and texto and len(texto.strip()) > 50:
                        logger.info(f"✓ PyPDF2 extrajo {len(texto)} chars de página {i+1}")
                        
                except Exception as e:
                    logger.debug(f"Error extrayendo página {i+1} con PyPDF2: {e}")
                    textos.append("")
            
            return textos
            
        except ImportError:
            if debug:
                logger.warning("PyPDF2 no instalado, saltando este método")
            return []
        except Exception as e:
            logger.error(f"Error con PyPDF2: {e}")
            return []
    
    @staticmethod
    def _extraer_tabla_pagina(pdf_path: str, num_pagina: int, debug: bool = False) -> str:
        """
        Extrae tabla de una página y la convierte a texto.
        Útil cuando el texto está dentro de celdas.
        """
        try:
            import pdfplumber
            
            with pdfplumber.open(pdf_path) as pdf:
                if num_pagina >= len(pdf.pages):
                    return ""
                
                page = pdf.pages[num_pagina]
                tables = page.extract_tables()
                
                if not tables:
                    return ""
                
                # Convertir tablas a texto
                texto_resultado = []
                for table in tables:
                    for row in table:
                        # Filtrar None y unir con espacios
                        row_text = " | ".join([str(cell) if cell else "" for cell in row])
                        if row_text.strip():
                            texto_resultado.append(row_text)
                
                texto = "\n".join(texto_resultado)
                
                if debug and texto:
                    logger.info(f"✓ Extraídas {len(tables)} tablas de página {num_pagina+1}")
                
                return texto
                
        except Exception as e:
            logger.debug(f"Error extrayendo tabla de página {num_pagina+1}: {e}")
            return ""
    
    @staticmethod
    def extraer_metadatos_primera_pagina(pdf_path: str, debug: bool = False) -> dict:
        """
        Extracción INTENSIVA de la primera página.
        Combina todos los métodos y extrae tablas.
        """
        metadatos = {}
        
        # Método 1: Texto normal
        textos = PDFTextExtractor.extraer_todas_paginas(pdf_path, debug)
        if textos and textos[0]:
            metadatos['texto_completo'] = textos[0]
        
        # Método 2: Extraer TODAS las tablas de página 1
        try:
            import pdfplumber
            
            with pdfplumber.open(pdf_path) as pdf:
                if len(pdf.pages) > 0:
                    page = pdf.pages[0]
                    
                    # Extraer tablas
                    tables = page.extract_tables()
                    metadatos['num_tablas'] = len(tables)
                    metadatos['tablas'] = tables
                    
                    if debug and tables:
                        logger.info(f"📊 Página 1: {len(tables)} tablas encontradas")
                        for i, table in enumerate(tables):
                            logger.info(f"  Tabla {i+1}: {len(table)} filas")
                            if table:
                                logger.info(f"    Primera fila: {table[0]}")
        
        except Exception as e:
            logger.error(f"Error extrayendo tablas: {e}")
        
        return metadatos


def test_extractor(pdf_path: str):
    """Función de prueba."""
    import logging
    logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
    
    print("="*60)
    print(f"Probando extracción de: {Path(pdf_path).name}")
    print("="*60)
    
    extractor = PDFTextExtractor()
    
    # Test 1: Extraer todas las páginas
    print("\n1️⃣ EXTRACCIÓN DE TODAS LAS PÁGINAS:")
    textos = extractor.extraer_todas_paginas(pdf_path, debug=True)
    
    for i, texto in enumerate(textos[:3], 1):
        print(f"\n--- PÁGINA {i} ({len(texto)} chars) ---")
        print(texto[:300] if texto else "[VACÍA]")
    
    # Test 2: Extracción intensiva página 1
    print("\n\n2️⃣ EXTRACCIÓN INTENSIVA PÁGINA 1:")
    metadatos = extractor.extraer_metadatos_primera_pagina(pdf_path, debug=True)
    
    if metadatos.get('tablas'):
        print(f"\n📊 {metadatos['num_tablas']} tablas encontradas en página 1")
        for i, table in enumerate(metadatos['tablas'], 1):
            print(f"\n--- Tabla {i} ({len(table)} filas) ---")
            for j, row in enumerate(table[:8], 1):  # Primeras 8 filas
                print(f"  Fila {j}: {row}")
    
    print("\n" + "="*60)
    print("✅ TEST COMPLETADO")
    print("="*60)


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        test_extractor(sys.argv[1])
    else:
        print("Uso: python pdf_text_extractor.py <archivo.pdf>")
