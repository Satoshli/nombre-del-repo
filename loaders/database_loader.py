"""
Cargador de datos a base de datos.
Separa la lógica de carga del orquestador principal.
"""

import logging
from typing import Dict
from config.database import db
from config.patterns import DEFAULT_VALUES

logger = logging.getLogger(__name__)


class DatabaseLoader:
    """
    Carga datos extraídos a la base de datos SQLite.
    
    Responsabilidades:
    - Crear/obtener centros
    - Insertar órdenes de trabajo
    - Insertar mediciones de sedimento
    - Manejo de duplicados
    """
    
    def __init__(self, estrategia_duplicados: str = 'SKIP'):
        """
        Args:
            estrategia_duplicados: 'SKIP', 'UPDATE', 'VERSION'
        """
        self.estrategia_duplicados = estrategia_duplicados
    
    def load(self, data: Dict) -> bool:
        """
        Carga datos completos a la base de datos.
        
        Args:
            data: Diccionario con metadatos, estaciones y mediciones
        
        Returns:
            True si carga exitosa
        """
        try:
            metadatos = data['metadatos']
            codigo_ot = metadatos['codigo_ot']
            
            logger.info(f"💾 Cargando OT {codigo_ot} a base de datos...")
            
            # 1. Verificar duplicados
            if self._existe_ot(codigo_ot):
                logger.warning(f"⚠️ OT {codigo_ot} ya existe (estrategia: {self.estrategia_duplicados})")
                
                if self.estrategia_duplicados == 'SKIP':
                    return False
                elif self.estrategia_duplicados == 'UPDATE':
                    self._eliminar_ot(codigo_ot)
                # VERSION: Se implementaría con un campo version_numero
            
            # 2. Crear/obtener centro
            centro_id = self._get_or_create_centro(metadatos)
            logger.info(f"  ✓ Centro ID: {centro_id}")
            
            # 3. Crear orden de trabajo
            ot_id = self._create_orden_trabajo(centro_id, metadatos, data)
            logger.info(f"  ✓ OT ID: {ot_id}")
            
            # 4. Cargar datos específicos según tipo
            tipo_informe = metadatos.get('tipo_informe', 'SEDIMENTO')
            
            if tipo_informe == 'SEDIMENTO':
                self._load_sedimento(ot_id, data)
            # TODO: elif tipo_informe == 'OXIGENO':
            # TODO: elif tipo_informe == 'VISUAL':
            
            logger.info(f"✅ Carga completada para OT {codigo_ot}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error cargando a BD: {e}", exc_info=True)
            return False
    
    def _existe_ot(self, codigo_ot: str) -> bool:
        """Verifica si una OT ya existe."""
        result = db.execute_query(
            "SELECT ot_id FROM ordenes_trabajo WHERE codigo_ot = ?",
            (codigo_ot,)
        )
        return len(result) > 0
    
    def _eliminar_ot(self, codigo_ot: str):
        """Elimina una OT existente (con CASCADE a mediciones)."""
        db.execute_non_query(
            "DELETE FROM ordenes_trabajo WHERE codigo_ot = ?",
            (codigo_ot,)
        )
        logger.info(f"  ♻️  OT {codigo_ot} eliminada para actualización")
    
    def _get_or_create_centro(self, metadatos: Dict) -> int:
        """Obtiene o crea un centro."""
        codigo_centro = metadatos.get('codigo_centro')
        
        if not codigo_centro:
            # Centro censurado
            codigo_ot = metadatos['codigo_ot']
            codigo_centro = f"{DEFAULT_VALUES['CENTRO_PREFIX']}{codigo_ot}"
            es_censurado = True
            logger.info(f"  🔒 Centro censurado: {codigo_centro}")
        else:
            es_censurado = False
            logger.info(f"  🏢 Centro identificado: {codigo_centro}")
        
        nombre_centro = metadatos.get('nombre_centro') or DEFAULT_VALUES['CENTRO_NOMBRE']
        
        centro_id = db.get_or_create_centro(
            codigo=codigo_centro,
            nombre=nombre_centro,
            es_censurado=es_censurado
        )
        
        return centro_id
    
    def _create_orden_trabajo(self, centro_id: int, metadatos: Dict, data: Dict) -> int:
        """Crea registro de orden de trabajo."""
        diagnostico = data.get('diagnostico', {})
        
        ot_data = {
            'codigo_ot': metadatos['codigo_ot'],
            'centro_id': centro_id,
            'tipo_informe': metadatos.get('tipo_informe', 'SEDIMENTO'),
            'tipo_monitoreo': metadatos.get('tipo_monitoreo', 'INFA'),
            'fecha_muestreo': metadatos.get('fecha_muestreo'),
            'condicion_centro': metadatos.get('condicion_centro', 'AEROBICO'),
            'numero_incumplimientos': (
                diagnostico.get('incumplimientos_mot', 0) +
                diagnostico.get('incumplimientos_ph_eh', 0)
            ),
            'requiere_revision': 0,
            'archivo_pdf_original': metadatos['nombre_archivo'],
        }
        
        ot_id = db.insert_with_identity('ordenes_trabajo', ot_data)
        return ot_id
    
    def _load_sedimento(self, ot_id: int, data: Dict):
        """Carga datos de sedimento."""
        estaciones = data.get('estaciones', [])
        mediciones_mot = data.get('mediciones_mot', [])
        mediciones_ph_redox = data.get('mediciones_ph_redox', [])
        promedios_mot = data.get('promedios_mot', [])
        promedios_ph_redox = data.get('promedios_ph_redox', [])
        
        # Mapeo código estación → ID
        estacion_ids = {}
        
        # 1. Cargar estaciones
        logger.info("  📍 Cargando estaciones...")
        for estacion in estaciones:
            estacion_data = {
                'ot_id': ot_id,
                'codigo_estacion': estacion['codigo'],
                'utm_este': estacion.get('utm_este'),
                'utm_norte': estacion.get('utm_norte'),
                'profundidad_m': estacion.get('profundidad_m'),
            }
            
            estacion_id = db.insert_with_identity('sedimento_estaciones', estacion_data)
            estacion_ids[estacion['codigo']] = estacion_id
        
        logger.info(f"  ✓ {len(estacion_ids)} estaciones")
        
        # 2. Cargar MOT (réplicas individuales)
        logger.info("  🧪 Cargando MOT...")
        for mot in mediciones_mot:
            codigo_est = mot['codigo_estacion']
            if codigo_est not in estacion_ids:
                continue
            
            # Buscar promedio de esta estación
            promedio = next(
                (p['mot_promedio'] for p in promedios_mot 
                 if p['codigo_estacion'] == codigo_est), 
                None
            )
            
            mot_record = {
                'estacion_id': estacion_ids[codigo_est],
                'codigo_muestra': mot['codigo_muestra'],
                'replica': mot['replica'],
                'peso_muestra_g': mot.get('peso_muestra_g'),
                'mot_porcentaje': mot['mot_porcentaje'],
                'promedio_estacion': promedio,
                'cumple_limite_infa': 1 if mot['mot_porcentaje'] <= 9.0 else 0,
                'cumple_limite_post': 1 if mot['mot_porcentaje'] <= 8.0 else 0,
            }
            
            db.insert_with_identity('sedimento_materia_organica', mot_record)
        
        logger.info(f"  ✓ {len(mediciones_mot)} mediciones MOT")
        
        # 3. Cargar pH/Redox (réplicas individuales)
        logger.info("  ⚗️  Cargando pH/Redox...")
        for pr in mediciones_ph_redox:
            codigo_est = pr['codigo_estacion']
            if codigo_est not in estacion_ids:
                continue
            
            # Buscar promedios de esta estación
            prom_data = next(
                (p for p in promedios_ph_redox 
                 if p['codigo_estacion'] == codigo_est),
                {}
            )
            
            # Calcular cumplimientos
            cumple_ph = None
            if pr.get('ph'):
                cumple_ph = 1 if pr['ph'] >= 7.1 else 0
            
            cumple_redox = None
            if pr.get('eh_mv'):
                cumple_redox = 1 if pr['eh_mv'] >= 50 else 0
            
            cumple_conjunto = None
            if cumple_ph is not None and cumple_redox is not None:
                cumple_conjunto = 1 if (cumple_ph and cumple_redox) else 0
            
            pr_record = {
                'estacion_id': estacion_ids[codigo_est],
                'codigo_muestra': pr['codigo_muestra'],
                'replica': pr['replica'],
                'ph': pr.get('ph'),
                'promedio_ph': prom_data.get('ph_promedio'),
                'potencial_redox_mv': pr.get('potencial_redox_mv'),
                'promedio_redox': prom_data.get('eh_promedio'),
                'temperatura_c': pr.get('temperatura_c'),
                'cumple_ph': cumple_ph,
                'cumple_redox': cumple_redox,
                'cumple_conjunto': cumple_conjunto,
            }
            
            db.insert_with_identity('sedimento_ph_redox', pr_record)
        
        logger.info(f"  ✓ {len(mediciones_ph_redox)} mediciones pH/Redox")
