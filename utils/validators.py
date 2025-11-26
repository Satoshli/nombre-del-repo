"""
Validadores de datos extraídos.
"""

import logging
from typing import Dict, List, Tuple

from config.extractor_config import RANGOS_VALIDACION

logger = logging.getLogger(__name__)


class DataValidator:
    """Valida rangos y consistencia de datos extraídos."""
    
    @staticmethod
    def validar_mot(valor: float) -> Tuple[bool, str]:
        """Valida valor de MOT."""
        if valor < 0 or valor > 100:
            return False, f"MOT fuera de rango (0-100): {valor}%"
        
        if valor > RANGOS_VALIDACION['MOT_WARNING']:
            return True, f"⚠️ MOT alto: {valor}% (>50%)"
        
        return True, ""
    
    @staticmethod
    def validar_ph(valor: float) -> Tuple[bool, str]:
        """Valida valor de pH."""
        if valor < 0 or valor > 14:
            return False, f"pH fuera de rango (0-14): {valor}"
        
        ph_min, ph_max = RANGOS_VALIDACION['PH_MARINO']
        if valor < ph_min or valor > ph_max:
            return True, f"⚠️ pH fuera de rango típico marino ({ph_min}-{ph_max}): {valor}"
        
        return True, ""
    
    @staticmethod
    def validar_redox(valor: float) -> Tuple[bool, str]:
        """Valida valor de Redox/Eh."""
        eh_min, eh_max = RANGOS_VALIDACION['REDOX']
        if valor < eh_min or valor > eh_max:
            return False, f"Eh fuera de rango ({eh_min} a {eh_max}): {valor} mV"
        
        return True, ""
    
    @staticmethod
    def validar_temperatura_sedimento(valor: float) -> Tuple[bool, str]:
        """Valida temperatura del sedimento."""
        temp_min, temp_max = RANGOS_VALIDACION['TEMP_SEDIMENTO']
        if valor < temp_min or valor > temp_max:
            return False, f"Temperatura fuera de rango típico ({temp_min}-{temp_max}°C): {valor}°C"
        
        return True, ""
    
    @classmethod
    def validar_mediciones_mot(cls, mediciones: List[Dict]) -> Dict:
        """Valida todas las mediciones de MOT."""
        errores = []
        warnings = []
        
        for med in mediciones:
            valor = med.get('mot_porcentaje')
            if valor is not None:
                valido, mensaje = cls.validar_mot(valor)
                
                if not valido:
                    errores.append({
                        'codigo': med.get('codigo_muestra'),
                        'mensaje': mensaje
                    })
                elif mensaje:
                    warnings.append({
                        'codigo': med.get('codigo_muestra'),
                        'mensaje': mensaje
                    })
        
        return {
            'valido': len(errores) == 0,
            'errores': errores,
            'warnings': warnings,
        }
    
    @classmethod
    def validar_mediciones_ph_redox(cls, mediciones: List[Dict]) -> Dict:
        """Valida todas las mediciones de pH/Redox."""
        errores = []
        warnings = []
        
        for med in mediciones:
            # Validar pH
            ph = med.get('ph')
            if ph is not None:
                valido, mensaje = cls.validar_ph(ph)
                if not valido:
                    errores.append({
                        'codigo': med.get('codigo_muestra'),
                        'parametro': 'pH',
                        'mensaje': mensaje
                    })
                elif mensaje:
                    warnings.append({
                        'codigo': med.get('codigo_muestra'),
                        'parametro': 'pH',
                        'mensaje': mensaje
                    })
            
            # Validar Eh
            eh = med.get('eh_mv')
            if eh is not None:
                valido, mensaje = cls.validar_redox(eh)
                if not valido:
                    errores.append({
                        'codigo': med.get('codigo_muestra'),
                        'parametro': 'Eh',
                        'mensaje': mensaje
                    })
        
        return {
            'valido': len(errores) == 0,
            'errores': errores,
            'warnings': warnings,
        }
