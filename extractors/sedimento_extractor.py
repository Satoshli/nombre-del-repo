"""
Extractor COMPLETO de datos de sedimento (RL-10).
Versión mejorada con:
- Extracción de réplicas individuales
- Manejo de tablas continuadas
- Extracción de ubicaciones (UTM, profundidad)
- Mejor parsing de MOT y pH/Redox
"""

import re
import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path

try:
    from extractors.base_extractor import BaseExtractor
except ImportError:
    # Fallback si no existe base_extractor
    from abc import ABC, abstractmethod
    
    class BaseExtractor(ABC):
        def __init__(self, pdf_path: str, metadatos: Dict):
            self.pdf_path = pdf_path
            self.metadatos = metadatos
            self.texto_completo = ""
        
        @abstractmethod
        def extraer(self) -> Dict:
            pass
        
        def _extraer_texto_completo(self) -> str:
            import pdfplumber
            with pdfplumber.open(self.pdf_path) as pdf:
                return "\n".join([p.extract_text() or "" for p in pdf.pages])

from config.extractor_config import CODIGO_PATTERNS

logger = logging.getLogger(__name__)


class SedimentoExtractor(BaseExtractor):
    """Extractor completo para informes de sedimento."""
    
    # Umbrales regulatorios (Res. Exenta 3612/09)
    UMBRALES = {
        'INFA': {'MOT': 9.0, 'pH': 7.1, 'Eh': 50},
        'INFA-POSTANAEROBICA': {'MOT': 8.0, 'pH': 7.1, 'Eh': 75},
        'CPS': {'MOT': 9.0, 'pH': 7.1, 'Eh': 50}
    }
    
    def extraer(self) -> Dict:
        """
        Extrae todos los datos del informe de sedimento.
        
        Returns:
            {
                'metadatos': {...},
                'ubicaciones': [...],  # Estaciones con UTM y profundidad
                'mediciones_mot': [...],  # Con réplicas individuales
                'mediciones_ph_redox': [...],  # Con réplicas individuales
                'diagnostico': {...}  # Estado anaeróbico
            }
        """
        logger.info(f"📄 Extrayendo sedimento: {Path(self.pdf_path).name}")
        
        try:
            # 1. Extraer texto completo
            self.texto_completo = self._extraer_texto_completo()
            
            # 2. Extraer ubicaciones (estaciones con coordenadas)
            ubicaciones = self._extraer_ubicaciones()
            
            # 3. Extraer MOT (con réplicas individuales)
            mediciones_mot = self._extraer_mot_con_replicas()
            
            # 4. Extraer pH/Redox (con réplicas individuales)
            mediciones_ph_redox = self._extraer_ph_redox_con_replicas()
            
            # 5. Consolidar estaciones únicas
            estaciones = self._consolidar_estaciones(
                ubicaciones, mediciones_mot, mediciones_ph_redox
            )
            
            # 6. Calcular promedios por estación
            promedios_mot = self._calcular_promedios_mot(mediciones_mot)
            promedios_ph_redox = self._calcular_promedios_ph_redox(mediciones_ph_redox)
            
            # 7. Determinar estado anaeróbico
            diagnostico = self._determinar_estado_centro(
                estaciones,
                promedios_mot,
                promedios_ph_redox,
                self.metadatos.get('tipo_monitoreo', 'INFA')
            )
            
            # 8. Preparar resultado
            resultado = {
                'metadatos': {
                    **self.metadatos,
                    'estado_anaerobico': diagnostico['es_anaerobico']
                },
                'ubicaciones': ubicaciones,
                'estaciones': estaciones,
                'mediciones_mot': mediciones_mot,
                'mediciones_ph_redox': mediciones_ph_redox,
                'promedios_mot': promedios_mot,
                'promedios_ph_redox': promedios_ph_redox,
                'diagnostico': diagnostico,
            }
            
            # 9. Log de resultados
            self._log_resultados(resultado)
            
            return resultado
            
        except Exception as e:
            logger.error(f"❌ Error en extracción: {e}", exc_info=True)
            raise
    
    def _extraer_ubicaciones(self) -> List[Dict]:
        """
        Extrae tabla de ubicaciones con UTM y profundidad.
        
        Busca tabla con formato:
        TIPO | ESTACIÓN | CÓDIGO | RÉPLICAS | UTM ESTE | UTM NORTE | PROFUNDIDAD
        """
        ubicaciones = []
        lineas = self.texto_completo.split('\n')
        
        # Buscar tabla de ubicación
        idx_inicio = None
        for i, linea in enumerate(lineas):
            if any(kw in linea.upper() for kw in ['UBICACIÓN', 'UBICACION', 'IDENTIFICACIÓN']):
                idx_inicio = i
                break
        
        if idx_inicio is None:
            logger.warning("⚠️ No se encontró tabla de ubicaciones")
            return []
        
        # Extraer datos
        for i in range(idx_inicio, min(idx_inicio + 50, len(lineas))):
            linea = lineas[i]
            
            # Detectar fin de tabla
            if any(kw in linea.upper() for kw in ['MATERIA', 'MOT', 'PH/REDOX']):
                break
            
            # Buscar línea con estación
            match_estacion = re.search(r'Estaci[óo]n\s+(\d+)', linea, re.IGNORECASE)
            if not match_estacion:
                match_estacion = re.search(r'E(\d+)', linea)
            
            if match_estacion:
                codigo_estacion = f"E{match_estacion.group(1)}"
                
                # Extraer números (UTM Este, Norte, Profundidad)
                numeros = re.findall(r'\d+[,.]?\d*', linea)
                
                utm_este = None
                utm_norte = None
                profundidad = None
                
                # UTM suele tener 6-7 dígitos
                for num_str in numeros:
                    try:
                        num = int(num_str.replace(',', '').replace('.', ''))
                        if 100000 <= num <= 9999999:  # Rango UTM
                            if utm_este is None:
                                utm_este = num
                            elif utm_norte is None:
                                utm_norte = num
                                break
                    except:
                        pass
                
                # Profundidad suele ser el último número (rango 1-100m típico)
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
        
        logger.info(f"✓ Ubicaciones: {len(ubicaciones)} estaciones")
        return ubicaciones
    
    def _extraer_mot_con_replicas(self) -> List[Dict]:
        """
        Extrae MOT con TODAS las réplicas individuales.
        
        Formato esperado:
        E1-R1 | 10.021 | 15.95
        E1-R2 | 10.002 | 9.11
        E1-R3 | 10.030 | 11.47 | 12.2 (promedio)
        """
        mediciones = []
        lineas = self.texto_completo.split('\n')
        
        # Buscar sección MOT
        idx_inicio = None
        for i, linea in enumerate(lineas):
            if 'MATERIA' in linea.upper() and ('ORGANICA' in linea.upper() or 'ORGÁNICA' in linea.upper()):
                idx_inicio = i
                break
        
        if idx_inicio is None:
            logger.warning("⚠️ No se encontró tabla MOT")
            return []
        
        # Extraer cada réplica
        estacion_actual = None
        replica_actual = None
        
        for i in range(idx_inicio, min(idx_inicio + 200, len(lineas))):
            linea = lineas[i]
            
            # Detectar fin (no antes de ANEXO)
            if any(kw in linea.upper() for kw in ['PH/REDOX', 'POTENCIAL', 'ANEXO', 'LÍMITES']):
                # Solo salir si ya tenemos datos
                if mediciones:
                    break
            
            # Detectar continuación de tabla
            if 'CONTINUACIÓN' in linea.upper() or 'CONTINUACION' in linea.upper():
                logger.debug("Tabla MOT continúa...")
                continue
            
            # Buscar código completo: E#-R#
            match = re.search(r'(E\d+)-(R\d+)', linea)
            if not match:
                continue
            
            codigo_estacion = match.group(1)  # E1
            codigo_replica = match.group(2)   # R1
            replica_num = int(codigo_replica[1:])
            
            # Extraer valores numéricos
            numeros = re.findall(r'\d+[,.]\d+', linea)
            
            if len(numeros) < 2:
                continue
            
            # Típicamente: peso_muestra | mot_valor | [promedio_estacion]
            try:
                peso_muestra = float(numeros[0].replace(',', '.'))
                mot_valor = float(numeros[1].replace(',', '.'))
                
                # Validar rangos
                if not (0.01 <= peso_muestra <= 15.0):
                    logger.debug(f"Peso muestra fuera de rango: {peso_muestra}")
                    continue
                
                if not (0.5 <= mot_valor <= 100):
                    logger.debug(f"MOT fuera de rango: {mot_valor}")
                    continue
                
                mediciones.append({
                    'codigo_estacion': codigo_estacion,
                    'codigo_muestra': f"{codigo_estacion}-{codigo_replica}",
                    'replica': replica_num,
                    'peso_muestra_g': round(peso_muestra, 3),
                    'mot_porcentaje': round(mot_valor, 2),
                })
                
            except (ValueError, IndexError) as e:
                logger.debug(f"Error parseando MOT en línea: {linea[:50]}")
                continue
        
        logger.info(f"✓ MOT: {len(mediciones)} mediciones")
        return mediciones
    
    def _extraer_ph_redox_con_replicas(self) -> List[Dict]:
        """
        Extrae pH y Redox con TODAS las réplicas individuales.
        
        Formato:
        E1-R1 | -343 | 6.9 | 10 | 217 | -126
        (potencial_redox_mv | ph | temp | factor | eh_mv)
        """
        mediciones = []
        lineas = self.texto_completo.split('\n')
        
        # Buscar sección pH/Redox
        idx_inicio = None
        for i, linea in enumerate(lineas):
            if 'PH/REDOX' in linea.upper() or 'POTENCIAL' in linea.upper():
                idx_inicio = i
                break
        
        if idx_inicio is None:
            logger.warning("⚠️ No se encontró tabla pH/Redox")
            return []
        
        for i in range(idx_inicio, min(idx_inicio + 200, len(lineas))):
            linea = lineas[i]
            
            # Fin de sección
            if any(kw in linea.upper() for kw in ['ANEXO', 'LÍMITES', 'LIMITE']):
                if mediciones:
                    break
            
            # Buscar E#-R#
            match = re.search(r'(E\d+)-(R\d+)', linea)
            if not match:
                continue
            
            codigo_estacion = match.group(1)
            codigo_replica = match.group(2)
            replica_num = int(codigo_replica[1:])
            
            # Extraer valores
            # pH: decimal entre 6.0-8.5
            # Potencial Redox: entero negativo típicamente
            # Eh: entero que puede ser negativo
            
            ph_valores = []
            redox_valores = []
            eh_valores = []
            temperatura = None
            
            # Buscar pH
            ph_matches = re.findall(r'(\d+[,.]\d+)', linea)
            for val_str in ph_matches:
                try:
                    val = float(val_str.replace(',', '.'))
                    if 6.0 <= val <= 8.5:
                        ph_valores.append(val)
                    elif 5.0 <= val <= 20.0:  # Temperatura
                        temperatura = val
                except:
                    pass
            
            # Buscar Redox/Eh (números negativos o grandes)
            numeros_todos = re.findall(r'-?\d+', linea)
            for num_str in numeros_todos:
                try:
                    num = int(num_str)
                    if -500 <= num <= -50:  # Potencial Redox típico
                        redox_valores.append(num)
                    elif -400 <= num <= 400:  # Eh puede ser positivo o negativo
                        eh_valores.append(num)
                except:
                    pass
            
            # Crear medición
            if ph_valores or eh_valores:
                mediciones.append({
                    'codigo_estacion': codigo_estacion,
                    'codigo_muestra': f"{codigo_estacion}-{codigo_replica}",
                    'replica': replica_num,
                    'ph': ph_valores[0] if ph_valores else None,
                    'potencial_redox_mv': redox_valores[0] if redox_valores else None,
                    'eh_mv': eh_valores[-1] if eh_valores else None,  # Último suele ser Eh
                    'temperatura_c': temperatura,
                })
        
        logger.info(f"✓ pH/Redox: {len(mediciones)} mediciones")
        return mediciones
    
    def _consolidar_estaciones(self, ubicaciones: List[Dict], 
                               mot: List[Dict], ph_redox: List[Dict]) -> List[Dict]:
        """Consolida estaciones únicas con su información."""
        codigos_unicos = set()
        
        for ub in ubicaciones:
            codigos_unicos.add(ub['codigo_estacion'])
        
        for med in mot + ph_redox:
            codigos_unicos.add(med['codigo_estacion'])
        
        estaciones = []
        for codigo in sorted(codigos_unicos):
            # Buscar ubicación
            ubicacion = next((u for u in ubicaciones if u['codigo_estacion'] == codigo), None)
            
            estacion = {
                'codigo': codigo,
                'utm_este': ubicacion['utm_este'] if ubicacion else None,
                'utm_norte': ubicacion['utm_norte'] if ubicacion else None,
                'profundidad_m': ubicacion['profundidad_m'] if ubicacion else None,
            }
            
            estaciones.append(estacion)
        
        return estaciones
    
    def _calcular_promedios_mot(self, mediciones: List[Dict]) -> List[Dict]:
        """Calcula promedios de MOT por estación."""
        promedios = {}
        
        for med in mediciones:
            codigo = med['codigo_estacion']
            if codigo not in promedios:
                promedios[codigo] = {
                    'valores': [],
                    'codigo_estacion': codigo,
                }
            promedios[codigo]['valores'].append(med['mot_porcentaje'])
        
        resultado = []
        for codigo, data in promedios.items():
            valores = data['valores']
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
                promedios[codigo] = {
                    'ph_valores': [],
                    'eh_valores': [],
                    'codigo_estacion': codigo,
                }
            
            if med['ph'] is not None:
                promedios[codigo]['ph_valores'].append(med['ph'])
            if med['eh_mv'] is not None:
                promedios[codigo]['eh_valores'].append(med['eh_mv'])
        
        resultado = []
        for codigo, data in promedios.items():
            ph_prom = None
            eh_prom = None
            
            if data['ph_valores']:
                ph_prom = round(sum(data['ph_valores']) / len(data['ph_valores']), 2)
            
            if data['eh_valores']:
                eh_prom = round(sum(data['eh_valores']) / len(data['eh_valores']), 0)
            
            resultado.append({
                'codigo_estacion': codigo,
                'ph_promedio': ph_prom,
                'eh_promedio': eh_prom,
            })
        
        return resultado
    
    def _determinar_estado_centro(self, estaciones: List[Dict],
                                   promedios_mot: List[Dict],
                                   promedios_ph_redox: List[Dict],
                                   tipo_monitoreo: str) -> Dict:
        """
        Determina si el centro es anaeróbico según Res. Exenta 3612/09.
        
        Criterios:
        - MOT: anaerób si >= 30% estaciones incumplen (3 de 8)
        - pH y Eh: anaerób si incumplen conjuntamente >= 30% estaciones
        """
        umbrales = self.UMBRALES.get(tipo_monitoreo, self.UMBRALES['INFA'])
        total_estaciones = len(estaciones)
        
        if total_estaciones == 0:
            return {
                'es_anaerobico': False,
                'incumplimientos_mot': 0,
                'incumplimientos_ph_eh': 0,
                'umbral_estaciones': 0,
                'detalles': 'Sin estaciones'
            }
        
        # Umbral: 30% de estaciones (mínimo 3 para 8 estaciones)
        umbral_incumplimientos = max(3, int(total_estaciones * 0.30))
        
        # Contar incumplimientos MOT
        incumplimientos_mot = 0
        for prom in promedios_mot:
            if prom['mot_promedio'] > umbrales['MOT']:
                incumplimientos_mot += 1
        
        # Contar incumplimientos pH y Eh conjuntos
        incumplimientos_ph_eh = 0
        for prom in promedios_ph_redox:
            incumple_ph = prom['ph_promedio'] is not None and prom['ph_promedio'] < umbrales['pH']
            incumple_eh = prom['eh_promedio'] is not None and prom['eh_promedio'] < umbrales['Eh']
            
            if incumple_ph and incumple_eh:
                incumplimientos_ph_eh += 1
        
        # Determinar si es anaeróbico
        es_anaerobico = (
            incumplimientos_mot >= umbral_incumplimientos or
            incumplimientos_ph_eh >= umbral_incumplimientos
        )
        
        diagnostico = {
            'es_anaerobico': es_anaerobico,
            'incumplimientos_mot': incumplimientos_mot,
            'incumplimientos_ph_eh': incumplimientos_ph_eh,
            'umbral_estaciones': umbral_incumplimientos,
            'total_estaciones': total_estaciones,
            'tipo_monitoreo': tipo_monitoreo,
            'umbrales_aplicados': umbrales,
        }
        
        logger.info(
            f"{'🔴 ANAERÓBICO' if es_anaerobico else '🟢 AERÓBICO'}: "
            f"MOT={incumplimientos_mot}/{total_estaciones}, "
            f"pH+Eh={incumplimientos_ph_eh}/{total_estaciones} "
            f"(umbral: {umbral_incumplimientos})"
        )
        
        return diagnostico
    
    def _log_resultados(self, resultado: Dict):
        """Log de resultados de extracción."""
        logger.info("=" * 60)
        logger.info(f"✅ Extracción completada:")
        logger.info(f"  📍 Ubicaciones: {len(resultado['ubicaciones'])}")
        logger.info(f"  🏢 Estaciones: {len(resultado['estaciones'])}")
        logger.info(f"  🧪 MOT (réplicas): {len(resultado['mediciones_mot'])}")
        logger.info(f"  ⚗️  pH/Redox (réplicas): {len(resultado['mediciones_ph_redox'])}")
        logger.info(f"  📊 Estado: {resultado['diagnostico']['es_anaerobico']}")
        logger.info("=" * 60)
