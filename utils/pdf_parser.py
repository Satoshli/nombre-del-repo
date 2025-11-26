"""
Utilidades básicas para parsing de PDFs.
Solo extracción de texto y tablas.
"""

import re
import logging
from typing import List
from pathlib import Path

import pdfplumber
import pandas as pd

logger = logging.getLogger(__name__)


def extraer_texto_completo(pdf_path: str) -> str:
    """Extrae todo el texto del PDF."""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            texto_paginas = []
            for page in pdf.pages:
                texto = page.extract_text()
                if texto:
                    texto_paginas.append(texto)
            
            texto_completo = "\n".join(texto_paginas)
            logger.debug(f"Texto extraído: {len(texto_completo)} caracteres")
            return texto_completo
            
    except Exception as e:
        logger.error(f"Error extrayendo texto: {str(e)}")
        return ""


def extraer_tablas(pdf_path: str, pagina: int = None) -> List[pd.DataFrame]:
    """Extrae tablas del PDF usando pdfplumber."""
    tablas = []
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            paginas = [pdf.pages[pagina]] if pagina else pdf.pages
            
            for page in paginas:
                try:
                    tables = page.extract_tables()
                    for table in tables:
                        if table and len(table) > 1:
                            df = pd.DataFrame(table[1:], columns=table[0])
                            df = df.applymap(lambda x: str(x).strip() if x else '')
                            df = df.replace('', pd.NA).dropna(how='all')
                            
                            if not df.empty:
                                tablas.append(df)
                                
                except Exception as e:
                    logger.debug(f"Error extrayendo tabla: {str(e)}")
                    continue
        
        return tablas
        
    except Exception as e:
        logger.error(f"Error en extracción de tablas: {str(e)}")
        return []


def validar_estructura_pdf(pdf_path: str) -> dict:
    """Valida que el PDF tenga estructura esperada."""
    resultado = {
        'valido': False,
        'tiene_texto': False,
        'tiene_tablas': False,
        'num_paginas': 0,
        'errores': []
    }
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            resultado['num_paginas'] = len(pdf.pages)
            
            if resultado['num_paginas'] == 0:
                resultado['errores'].append("PDF sin páginas")
                return resultado
            
            # Verificar texto
            texto = pdf.pages[0].extract_text()
            if texto and len(texto) > 100:
                resultado['tiene_texto'] = True
            else:
                resultado['errores'].append("Poco o ningún texto")
            
            # Verificar tablas
            for page in pdf.pages[:3]:
                tables = page.extract_tables()
                if tables:
                    resultado['tiene_tablas'] = True
                    break
            
            resultado['valido'] = resultado['tiene_texto']
        
        return resultado
        
    except Exception as e:
        resultado['errores'].append(f"Error: {str(e)}")
        return resultado


def limpiar_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Limpia DataFrame de valores vacíos."""
    if df.empty:
        return df
    
    df = df.dropna(how='all')
    df = df.dropna(axis=1, how='all')
    
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].str.strip()
    
    df = df.replace(['', 'nan', 'NaN', 'None'], None)
    
    return df
