"""
Orquestador principal del sistema de extracción.
Versión COMPLETA Y CORREGIDA con:
- MetadataExtractor con debug activado
- SedimentoExtractor mejorado con réplicas
- Validación de datos
- Carga completa a BD SQLite
"""

import click
import logging
import time
from pathlib import Path
from typing import List
from datetime import datetime
from tqdm import tqdm

from config.database import db
from config.settings import (
    INPUT_DIR, LOG_DIR, LOG_LEVEL, LOG_FORMAT, 
    LOG_DATE_FORMAT, DEFAULT_VALUES
)

# Imports de extractores
from extractors.metadata_extractor import MetadataExtractor
from extractors.sedimento_extractor import SedimentoExtractor
from utils.validators import DataValidator

# Configurar logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format=LOG_FORMAT,
    datefmt=LOG_DATE_FORMAT,
    handlers=[
        logging.FileHandler(Path(LOG_DIR) / 'procesamiento.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class ProcessingOrchestrator:
    """Orquestador del procesamiento de PDFs."""
    
    def __init__(self, dry_run: bool = False, debug: bool = False):
        self.dry_run = dry_run
        self.debug = debug
        self.stats = {
            'total': 0,
            'exitosos': 0,
            'fallidos': 0,
            'parciales': 0,
        }
    
    def process_directory(self, input_dir: str):
        """Procesa todos los PDFs en un directorio."""
        pdf_files = list(Path(input_dir).glob('*.pdf'))
        self.stats['total'] = len(pdf_files)
        
        if not pdf_files:
            logger.warning(f"No se encontraron archivos PDF en: {input_dir}")
            return
        
        logger.info(f"Encontrados {len(pdf_files)} archivos PDF para procesar")
        
        # Procesar cada PDF con barra de progreso
        for pdf_file in tqdm(pdf_files, desc="Procesando PDFs"):
            try:
                self.process_single_pdf(str(pdf_file))
            except Exception as e:
                logger.error(f"Error fatal procesando {pdf_file.name}: {e}", exc_info=True)
                self.stats['fallidos'] += 1
        
        # Reporte final
        self._print_summary()
    
    def process_single_pdf(self, pdf_path: str):
        """Procesa un PDF individual."""
        start_time = time.time()
        pdf_name = Path(pdf_path).name
        
        logger.info(f"\n{'='*60}")
        logger.info(f"📄 Procesando: {pdf_name}")
        logger.info(f"{'='*60}")
        
        try:
            # 1. Extraer metadatos (CON DEBUG ACTIVADO)
            logger.info("📋 Extrayendo metadatos...")
            metadatos = MetadataExtractor.extraer_todos(pdf_path, debug=self.debug)
            
            # Verificar metadatos críticos
            if not metadatos.get('codigo_ot'):
                logger.error("❌ No se pudo extraer código OT - ABORTANDO")
                self.stats['fallidos'] += 1
                return
            
            logger.info(f"✅ OT extraído: {metadatos['codigo_ot']}")
            
            # Detectar tipo de informe
            tipo_informe = self._detectar_tipo_informe(pdf_path, metadatos)
            metadatos['tipo_informe'] = tipo_informe
            
            logger.info(f"📊 Tipo de informe: {tipo_informe}")
            
            # 2. Seleccionar y ejecutar extractor apropiado
            if tipo_informe == 'SEDIMENTO':
                logger.info("🧪 Ejecutando extractor de sedimento...")
                extractor = SedimentoExtractor(pdf_path, metadatos)
                data = extractor.extraer()
                
                # 3. Validar datos extraídos
                logger.info("✅ Validando datos...")
                if not self._validar_datos_sedimento(data):
                    logger.error("⚠️ Validación con warnings - marcando para revisión")
                    data['metadatos']['requiere_revision'] = True
                
            elif tipo_informe == 'OXIGENO':
                logger.warning("⚠️ Extractor de oxígeno no implementado aún")
                self.stats['fallidos'] += 1
                return
                
            elif tipo_informe == 'VISUAL':
                logger.warning("⚠️ Extractor de registro visual no implementado aún")
                self.stats['fallidos'] += 1
                return
                
            else:
                logger.error(f"❌ Tipo de informe desconocido: {tipo_informe}")
                self.stats['fallidos'] += 1
                return
            
            # 4. Cargar a base de datos (si no es dry run)
            if not self.dry_run:
                logger.info("💾 Cargando a base de datos...")
                success = self._load_to_database(data)
                if success:
                    self.stats['exitosos'] += 1
                    logger.info("✅ Carga exitosa a BD")
                else:
                    self.stats['fallidos'] += 1
                    logger.error("❌ Error en carga a BD")
            else:
                logger.info("🔍 DRY RUN: No se cargó a base de datos")
                logger.info(f"   Registros que se cargarían:")
                logger.info(f"   - Estaciones: {len(data.get('estaciones', []))}")
                logger.info(f"   - MOT: {len(data.get('mediciones_mot', []))}")
                logger.info(f"   - pH/Redox: {len(data.get('mediciones_ph_redox', []))}")
                self.stats['exitosos'] += 1
            
            # 5. Tiempo de procesamiento
            elapsed = time.time() - start_time
            logger.info(f"⏱️ Procesamiento completado en {elapsed:.2f} segundos")
            
        except Exception as e:
            logger.error(f"❌ Error procesando {pdf_name}: {e}", exc_info=True)
            self.stats['fallidos'] += 1
    
    def _detectar_tipo_informe(self, pdf_path: str, metadatos: dict) -> str:
        """
        Detecta tipo de informe basándose en:
        1. Nombre del archivo
        2. Contenido del texto
        3. Palabras clave
        """
        import pdfplumber
        
        nombre = Path(pdf_path).stem.upper()
        
        # Detección por nombre de archivo
        if 'SEDIMENTO' in nombre or 'RL-10' in nombre or 'RL10' in nombre:
            return 'SEDIMENTO'
        elif 'OXIGENO' in nombre or 'OXYGEN' in nombre or 'RL-20' in nombre:
            return 'OXIGENO'
        elif 'VISUAL' in nombre or 'RL-30' in nombre:
            return 'VISUAL'
        
        # Detección por contenido
        try:
            with pdfplumber.open(pdf_path) as pdf:
                texto = ""
                for i in range(min(3, len(pdf.pages))):
                    texto += pdf.pages[i].extract_text() or ""
                
                texto_upper = texto.upper()
                
                # Contadores de keywords
                score_sedimento = 0
                score_oxigeno = 0
                score_visual = 0
                
                # Keywords de sedimento
                if 'MATERIA ORGANICA' in texto_upper or 'MOT' in texto_upper:
                    score_sedimento += 3
                if 'PH/REDOX' in texto_upper or 'POTENCIAL REDOX' in texto_upper:
                    score_sedimento += 2
                if 'REPLICA' in texto_upper:
                    score_sedimento += 1
                
                # Keywords de oxígeno
                if 'OXIGENO DISUELTO' in texto_upper:
                    score_oxigeno += 3
                if 'PERFIL' in texto_upper or 'COLUMNA DE AGUA' in texto_upper:
                    score_oxigeno += 2
                if 'SATURACION' in texto_upper:
                    score_oxigeno += 1
                
                # Keywords de visual
                if 'REGISTRO VISUAL' in texto_upper:
                    score_visual += 3
                if 'TRANSECTA' in texto_upper:
                    score_visual += 2
                if 'ABUNDANCIA' in texto_upper or 'PHYLLUM' in texto_upper:
                    score_visual += 1
                
                # Determinar ganador
                max_score = max(score_sedimento, score_oxigeno, score_visual)
                
                if max_score == 0:
                    logger.warning("No se detectaron keywords claras, asumiendo SEDIMENTO")
                    return 'SEDIMENTO'
                
                if score_sedimento == max_score:
                    return 'SEDIMENTO'
                elif score_oxigeno == max_score:
                    return 'OXIGENO'
                elif score_visual == max_score:
                    return 'VISUAL'
                
        except Exception as e:
            logger.error(f"Error detectando tipo de informe: {e}")
        
        # Default: SEDIMENTO
        logger.warning("Detección de tipo falló, asumiendo SEDIMENTO")
        return 'SEDIMENTO'
    
    def _validar_datos_sedimento(self, data: dict) -> bool:
        """
        Valida datos de sedimento extraídos.
        
        Returns:
            True si datos son válidos (sin errores críticos)
        """
        tiene_errores = False
        
        # Validar metadatos
        metadatos = data.get('metadatos', {})
        if not metadatos.get('codigo_ot'):
            logger.error("❌ Código OT faltante")
            return False
        
        # Validar que haya datos
        mediciones_mot = data.get('mediciones_mot', [])
        mediciones_ph_redox = data.get('mediciones_ph_redox', [])
        
        if len(mediciones_mot) == 0:
            logger.warning("⚠️ No se extrajo ningún dato de MOT")
        
        if len(mediciones_ph_redox) == 0:
            logger.warning("⚠️ No se extrajo ningún dato de pH/Redox")
        
        # Validar rangos de valores
        validacion_mot = DataValidator.validar_mediciones_mot(mediciones_mot)
        validacion_ph = DataValidator.validar_mediciones_ph_redox(mediciones_ph_redox)
        
        # Log warnings
        for warning in validacion_mot.get('warnings', []):
            logger.warning(f"  MOT: {warning.get('mensaje', warning)}")
        
        for warning in validacion_ph.get('warnings', []):
            logger.warning(f"  pH/Redox: {warning.get('mensaje', warning)}")
        
        # Log errores críticos
        if not validacion_mot.get('valido', True):
            logger.error("❌ Errores críticos en validación de MOT")
            for error in validacion_mot.get('errores', []):
                logger.error(f"  {error.get('mensaje', error)}")
            tiene_errores = True
        
        if not validacion_ph.get('valido', True):
            logger.error("❌ Errores críticos en validación de pH/Redox")
            for error in validacion_ph.get('errores', []):
                logger.error(f"  {error.get('mensaje', error)}")
            tiene_errores = True
        
        # Validar número esperado de mediciones
        num_estaciones = len(data.get('estaciones', []))
        
        if num_estaciones > 0:
            mot_esperado = num_estaciones * 3
            mot_obtenido = len(mediciones_mot)
            
            if mot_obtenido < mot_esperado * 0.5:  # Menos del 50%
                logger.warning(
                    f"⚠️ Pocas mediciones MOT: {mot_obtenido}/{mot_esperado} esperadas"
                )
        
        return not tiene_errores
    
    def _load_to_database(self, data: dict) -> bool:
        """Carga los datos a la base de datos SQLite."""
        try:
            metadatos = data['metadatos']
            codigo_ot = metadatos['codigo_ot']
            
            logger.info(f"📊 Cargando OT {codigo_ot}...")
            
            # 1. Verificar si OT ya existe
            existing = db.execute_query(
                "SELECT ot_id FROM ordenes_trabajo WHERE codigo_ot = ?",
                (codigo_ot,)
            )
            
            if existing:
                logger.warning(f"⚠️ OT {codigo_ot} ya existe en BD (estrategia: SKIP)")
                return False
            
            # 2. Obtener o crear centro
            codigo_centro = metadatos.get('codigo_centro')
            
            if not codigo_centro:
                # Generar código censurado
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
            
            logger.info(f"  ✓ Centro ID: {centro_id}")
            
            # 3. Crear orden de trabajo
            ot_data = {
                'codigo_ot': codigo_ot,
                'centro_id': centro_id,
                'tipo_informe': metadatos.get('tipo_informe', 'SEDIMENTO'),
                'tipo_monitoreo': metadatos.get('tipo_monitoreo', 'INFA'),
                'fecha_muestreo': metadatos.get('fecha_muestreo'),
                'condicion_centro': metadatos.get('condicion_centro', 'AEROBICO'),
                'numero_incumplimientos': data.get('diagnostico', {}).get('incumplimientos_mot', 0),
                'requiere_revision': 1 if metadatos.get('requiere_revision') else 0,
                'archivo_pdf_original': metadatos['nombre_archivo'],
            }
            
            ot_id = db.insert_with_identity('ordenes_trabajo', ot_data)
            logger.info(f"  ✓ OT ID: {ot_id}")
            
            # 4. Cargar datos de sedimento si aplica
            if data.get('mediciones_mot') or data.get('mediciones_ph_redox'):
                self._load_sedimento_data(ot_id, data)
            
            logger.info(f"✅ Carga completada para OT {codigo_ot}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error cargando a BD: {e}", exc_info=True)
            return False
    
    def _load_sedimento_data(self, ot_id: int, data: dict):
        """Carga datos de sedimento con réplicas individuales."""
        
        ubicaciones = data.get('ubicaciones', [])
        estaciones_info = data.get('estaciones', [])
        mediciones_mot = data.get('mediciones_mot', [])
        mediciones_ph_redox = data.get('mediciones_ph_redox', [])
        
        # Mapeo código estación -> ID
        estacion_ids = {}
        
        # 1. Cargar estaciones con ubicaciones
        logger.info("  📍 Cargando estaciones...")
        for estacion in estaciones_info:
            estacion_data = {
                'ot_id': ot_id,
                'codigo_estacion': estacion['codigo'],
                'utm_este': estacion.get('utm_este'),
                'utm_norte': estacion.get('utm_norte'),
                'profundidad_m': estacion.get('profundidad_m'),
            }
            
            estacion_id = db.insert_with_identity('sedimento_estaciones', estacion_data)
            estacion_ids[estacion['codigo']] = estacion_id
        
        logger.info(f"  ✓ {len(estacion_ids)} estaciones cargadas")
        
        # 2. Cargar MOT (todas las réplicas individuales)
        logger.info("  🧪 Cargando mediciones MOT...")
        for mot in mediciones_mot:
            codigo_est = mot['codigo_estacion']
            if codigo_est not in estacion_ids:
                logger.warning(f"  ⚠️ Estación {codigo_est} no encontrada para MOT")
                continue
            
            # Calcular promedio de estación
            promedio_estacion = None
            promedios_mot = data.get('promedios_mot', [])
            for prom in promedios_mot:
                if prom['codigo_estacion'] == codigo_est:
                    promedio_estacion = prom['mot_promedio']
                    break
            
            mot_record = {
                'estacion_id': estacion_ids[codigo_est],
                'codigo_muestra': mot['codigo_muestra'],
                'replica': mot['replica'],
                'peso_muestra_g': mot.get('peso_muestra_g'),
                'mot_porcentaje': mot['mot_porcentaje'],
                'promedio_estacion': promedio_estacion,
                'cumple_limite_infa': 1 if mot['mot_porcentaje'] <= 9.0 else 0,
                'cumple_limite_post': 1 if mot['mot_porcentaje'] <= 8.0 else 0,
            }
            
            db.insert_with_identity('sedimento_materia_organica', mot_record)
        
        logger.info(f"  ✓ {len(mediciones_mot)} mediciones MOT cargadas")
        
        # 3. Cargar pH/Redox (todas las réplicas individuales)
        logger.info("  ⚗️ Cargando mediciones pH/Redox...")
        for pr in mediciones_ph_redox:
            codigo_est = pr['codigo_estacion']
            if codigo_est not in estacion_ids:
                logger.warning(f"  ⚠️ Estación {codigo_est} no encontrada para pH/Redox")
                continue
            
            # Calcular promedios de estación
            promedio_ph = None
            promedio_eh = None
            promedios_pr = data.get('promedios_ph_redox', [])
            for prom in promedios_pr:
                if prom['codigo_estacion'] == codigo_est:
                    promedio_ph = prom.get('ph_promedio')
                    promedio_eh = prom.get('eh_promedio')
                    break
            
            # Determinar cumplimiento
            cumple_ph = None
            if pr.get('ph') is not None:
                cumple_ph = 1 if pr['ph'] >= 7.1 else 0
            
            cumple_redox = None
            if pr.get('eh_mv') is not None:
                cumple_redox = 1 if pr['eh_mv'] >= 50 else 0
            
            cumple_conjunto = None
            if cumple_ph is not None and cumple_redox is not None:
                cumple_conjunto = 1 if (cumple_ph and cumple_redox) else 0
            
            pr_record = {
                'estacion_id': estacion_ids[codigo_est],
                'codigo_muestra': pr['codigo_muestra'],
                'replica': pr['replica'],
                'ph': pr.get('ph'),
                'promedio_ph': promedio_ph,
                'potencial_redox_mv': pr.get('potencial_redox_mv'),
                'eh_mv': pr.get('eh_mv'),
                'promedio_redox': promedio_eh,
                'temperatura_c': pr.get('temperatura_c'),
                'cumple_ph': cumple_ph,
                'cumple_redox': cumple_redox,
                'cumple_conjunto': cumple_conjunto,
            }
            
            db.insert_with_identity('sedimento_ph_redox', pr_record)
        
        logger.info(f"  ✓ {len(mediciones_ph_redox)} mediciones pH/Redox cargadas")
    
    def _print_summary(self):
        """Imprime resumen de procesamiento."""
        logger.info("\n" + "="*60)
        logger.info("📊 RESUMEN DE PROCESAMIENTO")
        logger.info("="*60)
        logger.info(f"Total de archivos:  {self.stats['total']}")
        logger.info(f"✅ Exitosos:        {self.stats['exitosos']}")
        logger.info(f"❌ Fallidos:        {self.stats['fallidos']}")
        if self.stats['total'] > 0:
            tasa_exito = self.stats['exitosos']/self.stats['total']*100
            logger.info(f"📈 Tasa de éxito:   {tasa_exito:.1f}%")
        logger.info("="*60)


@click.command()
@click.option('--input-dir', default=INPUT_DIR, help='Directorio con PDFs')
@click.option('--dry-run', is_flag=True, help='Ejecutar sin cargar a BD')
@click.option('--debug', is_flag=True, help='Modo debug (muestra más información)')
@click.option('--single-file', help='Procesar un solo archivo PDF')
@click.option('--test-db', is_flag=True, help='Solo probar conexión a BD')
@click.option('--init-db', is_flag=True, help='Inicializar base de datos (crear schema)')
def main(input_dir, dry_run, debug, single_file, test_db, init_db):
    """Sistema de extracción de datos - Monitoreo ambiental."""
    
    logger.info("="*60)
    logger.info("🚀 SISTEMA DE EXTRACCIÓN DE DATOS - MONITOREO AMBIENTAL")
    logger.info("📦 Base de datos: SQLite (plug and play)")
    logger.info("="*60)
    
    # Inicializar BD si se solicita
    if init_db:
        logger.info("🔧 Inicializando base de datos...")
        if db.initialize_database():
            logger.info("✅ Base de datos inicializada exitosamente")
            logger.info(f"  📁 Ubicación: {db.db_path}")
            # Mostrar tablas creadas
            tables = db.get_all_tables()
            logger.info(f"  📊 Tablas creadas: {len(tables)}")
            for table in tables:
                logger.info(f"    - {table}")
        else:
            logger.error("❌ Error inicializando base de datos")
        return
    
    # Test de conexión
    if test_db:
        logger.info("🔍 Probando conexión a base de datos...")
        if db.test_connection():
            logger.info("✅ Conexión exitosa")
            logger.info(f"  📁 Base de datos: {db.db_path}")
            
            # Mostrar estadísticas
            tables = db.get_all_tables()
            if tables:
                logger.info(f"  📊 Tablas encontradas: {len(tables)}")
                for table in tables[:5]:  # Mostrar primeras 5
                    count = db.get_table_count(table)
                    logger.info(f"    - {table}: {count} registros")
                
                if len(tables) > 5:
                    logger.info(f"    ... y {len(tables)-5} tablas más")
            else:
                logger.warning("  ⚠️ No hay tablas. Ejecutar: python main.py --init-db")
        else:
            logger.error("❌ Conexión fallida")
        return
    
    # Crear orquestador con debug
    orchestrator = ProcessingOrchestrator(dry_run=dry_run, debug=debug)
    
    # Procesar archivo único o directorio
    if single_file:
        if not Path(single_file).exists():
            logger.error(f"❌ Archivo no encontrado: {single_file}")
            return
        orchestrator.process_single_pdf(single_file)
    else:
        orchestrator.process_directory(input_dir)


if __name__ == '__main__':
    main()
