"""
Extractor simplificado para informes de sedimento (RL-10).
Versión refactorizada - sin duplicación de código.
"""

import re
import logging
from typing import Dict, List, Optional

from config.patterns import (
    SAMPLE_CODE_PATTERNS, 
    REGULATORY_LIMITS,
    ANAEROBIC_THRESHOLD,
    ANAEROBIC_MIN_STATIONS
)

logger = logging.getLogger(__name__)


class SedimentoExtractor:
    """Extractor para informes de sedimento."""
    
    def __init__(self, pdf_path: str, metadatos: Dict, textos: List[str]):
        self.pdf_path = pdf_path
        self.metadatos = metadatos
        self.textos = textos
        self.texto_completo = "\n".join(textos)
    
    def extraer(self) -> Dict:
        """
        Extrae todos los datos del informe de sedimento.
        
        Returns:
            Dict completo con metadatos, ubicaciones, mediciones y diagnóstico
        """
        logger.info(f"📄 Extrayendo sedimento: {self.metadatos['nombre_archivo']}")
        
        # 1. Extraer ubicaciones (con UTM)
        ubicaciones = self._extraer_ubicaciones()
        
        # 2. Extraer MOT (todas las réplicas)
        mediciones_mot = self._extraer_mot()
        
        # 3. Extraer pH/Redox (todas las réplicas)
        mediciones_ph_redox = self._extraer_ph_redox()
        
        # 4. Consolidar estaciones
        estaciones = self._consolidar_estaciones(ubicaciones, mediciones_mot)
        
        # 5. Calcular promedios
        promedios_mot = self._calcular_promedios_mot(mediciones_mot)
        promedios_ph_redox = self._calcular_promedios_ph_redox(mediciones_ph_redox)
        
        # 6. Diagnosticar estado del centro
        diagnostico = self._diagnosticar_estado(
            estaciones, promedios_mot, promedios_ph_redox
        )
        
        # 7. Actualizar metadatos con diagnóstico
        self.metadatos['condicion_centro'] = (
            'ANAEROBICO' if diagnostico['es_anaerobico'] else 'AEROBICO'
        )
        
        # 8. Log de resultados
        logger.info(f"✓ Ubicaciones: {len(ubicaciones)} estaciones")
        logger.info(f"✓ MOT: {len(mediciones_mot)} mediciones")
        logger.info(f"✓ pH/Redox: {len(mediciones_ph_redox)} mediciones")
        logger.info(
            f"{'🔴 ANAERÓBICO' if diagnostico['es_anaerobico'] else '🟢 AERÓBICO'}: "
            f"MOT={diagnostico['incumplimientos_mot']}/{diagnostico['total_estaciones']}, "
            f"pH+Eh={diagnostico['incumplimientos_ph_eh']}/{diagnostico['total_estaciones']} "
            f"(umbral: {diagnostico['umbral_estaciones']})"
        )
        
        return {
            'metadatos': self.metadatos,
            'ubicaciones': ubicaciones,
            'estaciones': estaciones,
            'mediciones_mot': mediciones_mot,
            'mediciones_ph_redox': mediciones_ph_redox,
            'promedios_mot': promedios_mot,
            'promedios_ph_redox': promedios_ph_redox,
            'diagnostico': diagnostico,
        }
    
    def _extraer_ubicaciones(self) -> List[Dict]:
        """Extrae tabla de ubicaciones con UTM y profundidad."""
        ubicaciones = []
        lineas = self.texto_completo.split('\n')
        
        # Buscar inicio de tabla de ubicación
        idx_inicio = None
        for i, linea in enumerate(lineas):
            if any(kw in linea.upper() for kw in ['UBICACIÓN', 'IDENTIFICACIÓN']):
                idx_inicio = i
                break
        
        if idx_inicio is None:
            logger.warning("⚠️ Tabla de ubicaciones no encontrada")
            return []
        
        # Extraer datos de estaciones
        for i in range(idx_inicio, min(idx_inicio + 50, len(lineas))):
            linea = lineas[i]
            
            # Detectar fin de tabla
            if any(kw in linea.upper() for kw in ['MATERIA', 'MOT', 'PH/REDOX']):
                break
            
            # Buscar código de estación
            match = re.search(r'(E\d+)', linea)
            if not match:
                continue
            
            codigo_estacion = match.group(1)
            
            # Extraer números (UTM Este, Norte, Profundidad)
            numeros = re.findall(r'\d+[,.]?\d*', linea)
            
            utm_este = None
            utm_norte = None
            profundidad = None
            
            # UTM tiene 6-7 dígitos
            for num_str in numeros:
                try:
                    num = int(num_str.replace(',', '').replace('.', ''))
                    if 100000 <= num <= 9999999:
                        if utm_este is None:
                            utm_este = num
                        elif utm_norte is None:
                            utm_norte = num
                            break
                except:
                    pass
            
            # Profundidad es el último número pequeño
            for num_str in reversed(numeros):
                try:
                    num = float(num_str.replace(',', '.'))
                    if 1 <= num <= 300:
                        profundidad = num
                        break
                except:
                    pass
            
            ubicaciones.append({
                'codigo_estacion': codigo_estacion,
                'utm_este': utm_este,
                'utm_norte': utm_norte,
                'profundidad_m': profundidad,
            })
        
        return ubicaciones
    
    def _extraer_mot(self) -> List[Dict]:
        """Extrae MOT con todas las réplicas individuales."""
        mediciones = []
        lineas = self.texto_completo.split('\n')
        
        # Buscar tabla MOT
        idx_inicio = None
        for i, linea in enumerate(lineas):
            if 'MATERIA' in linea.upper() and 'ORGANICA' in linea.upper():
                idx_inicio = i
                break
        
        if idx_inicio is None:
            logger.warning("⚠️ Tabla MOT no encontrada")
            return []
        
        # Extraer mediciones
        for i in range(idx_inicio, min(idx_inicio + 200, len(lineas))):
            linea = lineas[i]
            
            # Fin de tabla
            if any(kw in linea.upper() for kw in ['PH/REDOX', 'POTENCIAL', 'ANEXO']):
                if mediciones:  # Solo salir si ya hay datos
                    break
            
            # Buscar código E#-R#
            match = re.search(SAMPLE_CODE_PATTERNS['estacion_replica'], linea)
            if not match:
                continue
            
            codigo_estacion = match.group(1)
            codigo_replica = match.group(2)
            replica_num = int(codigo_replica[1:])
            
            # Extraer valores numéricos
            numeros = re.findall(r'\d+[,.]\d+', linea)
            
            if len(numeros) < 2:
                continue
            
            try:
                peso_muestra = float(numeros[0].replace(',', '.'))
                mot_valor = float(numeros[1].replace(',', '.'))
                
                # Validar rangos
                if not (0.01 <= peso_muestra <= 15.0):
                    continue
                
                if not (0.5 <= mot_valor <= 100):
                    continue
                
                mediciones.append({
                    'codigo_estacion': codigo_estacion,
                    'codigo_muestra': f"{codigo_estacion}-{codigo_replica}",
                    'replica': replica_num,
                    'peso_muestra_g': round(peso_muestra, 3),
                    'mot_porcentaje': round(mot_valor, 2),
                })
            except (ValueError, IndexError):
                continue
        
        return mediciones
    
    def _extraer_ph_redox(self) -> List[Dict]:
        """Extrae pH y Redox con todas las réplicas individuales."""
        mediciones = []
        lineas = self.texto_completo.split('\n')
        
        # Buscar tabla pH/Redox
        idx_inicio = None
        for i, linea in enumerate(lineas):
            if 'PH/REDOX' in linea.upper() or 'POTENCIAL' in linea.upper():
                idx_inicio = i
                break
        
        if idx_inicio is None:
            logger.warning("⚠️ Tabla pH/Redox no encontrada")
            return []
        
        for i in range(idx_inicio, min(idx_inicio + 200, len(lineas))):
            linea = lineas[i]
            
            # Fin de sección
            if any(kw in linea.upper() for kw in ['ANEXO', 'LÍMITE']):
                if mediciones:
                    break
            
            # Buscar E#-R#
            match = re.search(SAMPLE_CODE_PATTERNS['estacion_replica'], linea)
            if not match:
                continue
            
            codigo_estacion = match.group(1)
            codigo_replica = match.group(2)
            replica_num = int(codigo_replica[1:])
            
            # Extraer valores
            ph = None
            potencial_redox = None
            eh = None
            temperatura = None
            
            # pH: decimal entre 6.0-8.5
            ph_matches = re.findall(r'(\d+[,.]\d+)', linea)
            for val_str in ph_matches:
                try:
                    val = float(val_str.replace(',', '.'))
                    if 6.0 <= val <= 8.5:
                        ph = val
                    elif 5.0 <= val <= 20.0:
                        temperatura = val
                except:
                    pass
            
            # Redox/Eh: números (pueden ser negativos)
            numeros_todos = re.findall(r'-?\d+', linea)
            for num_str in numeros_todos:
                try:
                    num = int(num_str)
                    if -500 <= num <= -50:
                        potencial_redox = num
                    elif -400 <= num <= 400:
                        eh = num
                except:
                    pass
            
            if ph or eh:
                mediciones.append({
                    'codigo_estacion': codigo_estacion,
                    'codigo_muestra': f"{codigo_estacion}-{codigo_replica}",
                    'replica': replica_num,
                    'ph': ph,
                    'potencial_redox_mv': potencial_redox,
                    'eh_mv': eh,
                    'temperatura_c': temperatura,
                })
        
        return mediciones
    
    def _consolidar_estaciones(self, ubicaciones: List[Dict], 
                               mediciones_mot: List[Dict]) -> List[Dict]:
        """Consolida estaciones únicas."""
        codigos_unicos = set()
        
        for ub in ubicaciones:
            codigos_unicos.add(ub['codigo_estacion'])
        
        for med in mediciones_mot:
            codigos_unicos.add(med['codigo_estacion'])
        
        estaciones = []
        for codigo in sorted(codigos_unicos):
            ubicacion = next((u for u in ubicaciones if u['codigo_estacion'] == codigo), None)
            
            estaciones.append({
                'codigo': codigo,
                'utm_este': ubicacion['utm_este'] if ubicacion else None,
                'utm_norte': ubicacion['utm_norte'] if ubicacion else None,
                'profundidad_m': ubicacion['profundidad_m'] if ubicacion else None,
            })
        
        return estaciones
    
    def _calcular_promedios_mot(self, mediciones: List[Dict]) -> List[Dict]:
        """Calcula promedios de MOT por estación."""
        promedios = {}
        
        for med in mediciones:
            codigo = med['codigo_estacion']
            if codigo not in promedios:
                promedios[codigo] = []
            promedios[codigo].append(med['mot_porcentaje'])
        
        resultado = []
        for codigo, valores in promedios.items():
            resultado.append({
                'codigo_estacion': codigo,
                'mot_promedio': round(sum(valores) / len(valores), 2),
                'num_replicas': len(valores),
            })
        
        return resultado
    
    def _calcular_promedios_ph_redox(self, mediciones: List[Dict]) -> List[Dict]:
        """Calcula promedios de pH y Eh por estación."""
        promedios = {}
        
        for med in mediciones:
            codigo = med['codigo_estacion']
            if codigo not in promedios:
                promedios[codigo] = {'ph': [], 'eh': []}
            
            if med['ph']:
                promedios[codigo]['ph'].append(med['ph'])
            if med['eh_mv']:
                promedios[codigo]['eh'].append(med['eh_mv'])
        
        resultado = []
        for codigo, datos in promedios.items():
            ph_prom = round(sum(datos['ph']) / len(datos['ph']), 2) if datos['ph'] else None
            eh_prom = round(sum(datos['eh']) / len(datos['eh']), 0) if datos['eh'] else None
            
            resultado.append({
                'codigo_estacion': codigo,
                'ph_promedio': ph_prom,
                'eh_promedio': eh_prom,
            })
        
        return resultado
    
    def _diagnosticar_estado(self, estaciones: List[Dict], 
                            promedios_mot: List[Dict],
                            promedios_ph_redox: List[Dict]) -> Dict:
        """
        Determina si el centro es anaeróbico según Res. Exenta 3612/09.
        """
        tipo_monitoreo = self.metadatos.get('tipo_monitoreo', 'INFA')
        umbrales = REGULATORY_LIMITS.get(tipo_monitoreo, REGULATORY_LIMITS['INFA'])
        
        total_estaciones = len(estaciones)
        
        if total_estaciones == 0:
            return {
                'es_anaerobico': False,
                'incumplimientos_mot': 0,
                'incumplimientos_ph_eh': 0,
                'umbral_estaciones': 0,
                'total_estaciones': 0,
            }
        
        # Umbral: 30% o mínimo 3 estaciones
        umbral = max(ANAEROBIC_MIN_STATIONS, int(total_estaciones * ANAEROBIC_THRESHOLD))
        
        # Contar incumplimientos MOT
        incumplimientos_mot = sum(
            1 for p in promedios_mot 
            if p['mot_promedio'] > umbrales['MOT']
        )
        
        # Contar incumplimientos pH y Eh conjuntos
        incumplimientos_ph_eh = 0
        for prom in promedios_ph_redox:
            incumple_ph = prom['ph_promedio'] and prom['ph_promedio'] < umbrales['pH']
            incumple_eh = prom['eh_promedio'] and prom['eh_promedio'] < umbrales['Eh']
            
            if incumple_ph and incumple_eh:
                incumplimientos_ph_eh += 1
        
        # Determinar si es anaeróbico
        es_anaerobico = (
            incumplimientos_mot >= umbral or
            incumplimientos_ph_eh >= umbral
        )
        
        return {
            'es_anaerobico': es_anaerobico,
            'incumplimientos_mot': incumplimientos_mot,
            'incumplimientos_ph_eh': incumplimientos_ph_eh,
            'umbral_estaciones': umbral,
            'total_estaciones': total_estaciones,
            'tipo_monitoreo': tipo_monitoreo,
            'umbrales_aplicados': umbrales,
        }
