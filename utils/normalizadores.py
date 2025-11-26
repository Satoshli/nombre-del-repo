"""
Normalizadores de valores extraídos.
"""

import re
from typing import Optional


def normalizar_numero_decimal(valor_str: str) -> Optional[float]:
    """Convierte string a decimal (maneja coma y punto)."""
    if not valor_str:
        return None
    
    try:
        # Reemplazar coma por punto
        valor_limpio = str(valor_str).replace(',', '.')
        return float(valor_limpio)
    except:
        return None


def normalizar_codigo_estacion(codigo: str) -> str:
    """Normaliza código de estación a formato E#."""
    match = re.search(r'E?(\d+)', codigo, re.IGNORECASE)
    if match:
        return f"E{match.group(1)}"
    return codigo


def normalizar_codigo_replica(codigo: str) -> str:
    """Normaliza código de réplica a formato R#."""
    match = re.search(r'R?(\d+)', codigo, re.IGNORECASE)
    if match:
        return f"R{match.group(1)}"
    return codigo


def normalizar_codigo_muestra(estacion: str, replica: str) -> str:
    """Genera código de muestra estándar E#-R#."""
    est = normalizar_codigo_estacion(estacion)
    rep = normalizar_codigo_replica(replica)
    return f"{est}-{rep}"
