"""
Clase base para todos los extractores.
"""

import logging
from typing import Dict, Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BaseExtractor(ABC):
    """Clase base abstracta para extractores."""
    
    def __init__(self, pdf_path: str, metadatos: Dict):
        self.pdf_path = pdf_path
        self.metadatos = metadatos
        self.texto_completo = ""
        
    @abstractmethod
    def extraer(self) -> Dict:
        """
        Método principal de extracción.
        Debe ser implementado por cada extractor específico.
        """
        pass
    
    def _extraer_texto_completo(self) -> str:
        """Extrae todo el texto del PDF."""
        import pdfplumber
        
        with pdfplumber.open(self.pdf_path) as pdf:
            textos = []
            for page in pdf.pages:
                texto = page.extract_text()
                if texto:
                    textos.append(texto)
            return "\n".join(textos)
    
    def _validar_resultado(self, resultado: Dict) -> bool:
        """Valida que el resultado tenga la estructura esperada."""
        if not resultado:
            return False
        
        if 'metadatos' not in resultado:
            logger.error("Resultado sin metadatos")
            return False
        
        return True
    
    def _log_extraccion(self, tipo_dato: str, cantidad: int):
        """Log estandarizado de extracción."""
        logger.info(f"✓ Extraídos {cantidad} {tipo_dato}")
