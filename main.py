"""
Orquestador principal del sistema de extracción.
Versión refactorizada - simple, limpia y modular.
"""

import click
import logging
import time
from pathlib import Path
from typing import List

from config.database import db
from config.settings import INPUT_DIR, LOG_DIR, LOG_LEVEL, LOG_FORMAT, LOG_DATE_FORMAT
from config.patterns import REPORT_TYPE_KEYWORDS

from core.pdf_reader import PDFReader
from core.metadata import MetadataExtractor
from extractors.sedimento import SedimentoExtractor
from loaders.database_loader import DatabaseLoader

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


class ProcessingPipeline:
    """
    Pipeline simplificado de procesamiento.
    
    Flujo:
    1. Leer PDF (PDFReader)
    2. Extraer metadatos (MetadataExtractor con OCR automático)
    3. Detectar tipo de informe
    4. Ejecutar extractor específico
    5. Cargar a base de datos (DatabaseLoader)
    """
    
    def __init__(self, dry_run: bool = False, debug: bool = False):
        self.dry_run = dry_run
        self.debug = debug
        self.loader = DatabaseLoader()
        
        self.stats = {
            'total': 0,
            'exitosos': 0,
            'fallidos': 0,
        }
    
    def process_file(self, pdf_path: str) -> bool:
        """
        Procesa un archivo PDF individual.
        
        Returns:
            True si procesamiento exitoso
        """
        start_time = time.time()
        pdf_name = Path(pdf_path).name
        
        logger.info("\n" + "=" * 60)
        logger.info(f"📄 Procesando: {pdf_name}")
        logger.info("=" * 60)
        
        try:
            # 1. Leer PDF
            logger.info("📖 Leyendo PDF...")
            reader = PDFReader(pdf_path)
            textos = reader.extract_all_pages_text(debug=self.debug)
            
            if not textos or all(not t for t in textos):
                logger.error("❌ No se pudo extraer texto del PDF")
                return False
            
            # 2. Extraer metadatos (con OCR automático)
            logger.info("📋 Extrayendo metadatos...")
            metadatos = MetadataExtractor.extract_all(pdf_path, textos, debug=self.debug)
            
            if not metadatos.get('codigo_ot'):
                logger.error("❌ No se pudo extraer código OT")
                return False
            
            logger.info(f"✅ OT: {metadatos['codigo_ot']}")
            
            # 3. Detectar tipo de informe
            tipo_informe = self._detect_report_type(textos, pdf_name)
            metadatos['tipo_informe'] = tipo_informe
            
            logger.info(f"📊 Tipo: {tipo_informe}")
            
            # 4. Ejecutar extractor específico
            data = self._extract_data(tipo_informe, pdf_path, metadatos, textos)
            
            if not data:
                logger.error("❌ Extracción falló")
                return False
            
            # 5. Cargar a BD (si no es dry run)
            if not self.dry_run:
                logger.info("💾 Cargando a base de datos...")
                success = self.loader.load(data)
                
                if not success:
                    logger.error("❌ Error en carga a BD")
                    return False
                
                logger.info("✅ Carga exitosa")
            else:
                logger.info("🔍 DRY RUN - No se cargó a BD")
                self._show_dry_run_stats(data)
            
            # 6. Tiempo de procesamiento
            elapsed = time.time() - start_time
            logger.info(f"⏱️  Completado en {elapsed:.2f} segundos")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error procesando {pdf_name}: {e}", exc_info=True)
            return False
    
    def process_directory(self, directory: str):
        """Procesa todos los PDFs en un directorio."""
        pdf_files = list(Path(directory).glob('*.pdf'))
        
        if not pdf_files:
            logger.warning(f"No se encontraron PDFs en: {directory}")
            return
        
        self.stats['total'] = len(pdf_files)
        logger.info(f"📂 Encontrados {len(pdf_files)} archivos PDF")
        
        for pdf_file in pdf_files:
            success = self.process_file(str(pdf_file))
            
            if success:
                self.stats['exitosos'] += 1
            else:
                self.stats['fallidos'] += 1
        
        self._show_summary()
    
    def _detect_report_type(self, textos: List[str], filename: str) -> str:
        """
        Detecta tipo de informe.
        
        Estrategias:
        1. Keywords en nombre de archivo
        2. Keywords en texto (primeras 3 páginas)
        """
        # 1. Por nombre de archivo
        filename_upper = filename.upper()
        
        if 'SEDIMENTO' in filename_upper or 'RL-10' in filename_upper:
            return 'SEDIMENTO'
        elif 'OXIGENO' in filename_upper or 'RL-20' in filename_upper:
            return 'OXIGENO'
        elif 'VISUAL' in filename_upper or 'RL-30' in filename_upper:
            return 'VISUAL'
        
        # 2. Por contenido (primeras 3 páginas)
        texto = " ".join(textos[:3]).upper()
        
        score_sedimento = sum(1 for kw in REPORT_TYPE_KEYWORDS['SEDIMENTO'] if kw in texto)
        score_oxigeno = sum(1 for kw in REPORT_TYPE_KEYWORDS['OXIGENO'] if kw in texto)
        score_visual = sum(1 for kw in REPORT_TYPE_KEYWORDS['VISUAL'] if kw in texto)
        
        max_score = max(score_sedimento, score_oxigeno, score_visual)
        
        if max_score == 0:
            logger.warning("No se detectaron keywords, asumiendo SEDIMENTO")
            return 'SEDIMENTO'
        
        if score_sedimento == max_score:
            return 'SEDIMENTO'
        elif score_oxigeno == max_score:
            return 'OXIGENO'
        else:
            return 'VISUAL'
    
    def _extract_data(self, tipo_informe: str, pdf_path: str, 
                     metadatos: dict, textos: List[str]) -> dict:
        """Ejecuta el extractor apropiado según el tipo."""
        
        if tipo_informe == 'SEDIMENTO':
            logger.info("🧪 Ejecutando extractor de sedimento...")
            extractor = SedimentoExtractor(pdf_path, metadatos, textos)
            return extractor.extraer()
        
        elif tipo_informe == 'OXIGENO':
            logger.warning("⚠️ Extractor de oxígeno no implementado")
            return None
        
        elif tipo_informe == 'VISUAL':
            logger.warning("⚠️ Extractor visual no implementado")
            return None
        
        else:
            logger.error(f"❌ Tipo desconocido: {tipo_informe}")
            return None
    
    def _show_dry_run_stats(self, data: dict):
        """Muestra estadísticas en modo dry run."""
        logger.info("   Registros que se cargarían:")
        logger.info(f"   - Estaciones: {len(data.get('estaciones', []))}")
        logger.info(f"   - MOT: {len(data.get('mediciones_mot', []))}")
        logger.info(f"   - pH/Redox: {len(data.get('mediciones_ph_redox', []))}")
    
    def _show_summary(self):
        """Muestra resumen de procesamiento."""
        logger.info("\n" + "=" * 60)
        logger.info("📊 RESUMEN DE PROCESAMIENTO")
        logger.info("=" * 60)
        logger.info(f"Total:     {self.stats['total']}")
        logger.info(f"✅ Éxito:  {self.stats['exitosos']}")
        logger.info(f"❌ Fallos: {self.stats['fallidos']}")
        
        if self.stats['total'] > 0:
            tasa = self.stats['exitosos'] / self.stats['total'] * 100
            logger.info(f"📈 Tasa de éxito: {tasa:.1f}%")
        
        logger.info("=" * 60)


@click.command()
@click.option('--file', help='Archivo PDF específico')
@click.option('--dir', 'directory', default=INPUT_DIR, help='Directorio con PDFs')
@click.option('--dry-run', is_flag=True, help='No cargar a BD')
@click.option('--debug', is_flag=True, help='Modo debug')
@click.option('--init-db', is_flag=True, help='Inicializar base de datos')
@click.option('--test-db', is_flag=True, help='Probar conexión a BD')
def main(file, directory, dry_run, debug, init_db, test_db):
    """
    Sistema de extracción de datos - Monitoreo Ambiental.
    Versión refactorizada - Simple y modular.
    """
    
    logger.info("=" * 60)
    logger.info("🚀 SISTEMA DE EXTRACCIÓN - MONITOREO AMBIENTAL")
    logger.info("📦 Base de datos: SQLite (plug and play)")
    logger.info("=" * 60)
    
    # Comando: Inicializar BD
    if init_db:
        logger.info("🔧 Inicializando base de datos...")
        if db.initialize_database():
            logger.info("✅ Base de datos inicializada")
            
            tables = db.get_all_tables()
            logger.info(f"📊 Tablas: {len(tables)}")
            for table in tables:
                logger.info(f"  - {table}")
        else:
            logger.error("❌ Error inicializando BD")
        return
    
    # Comando: Test de conexión
    if test_db:
        logger.info("🔍 Probando conexión a BD...")
        if db.test_connection():
            logger.info("✅ Conexión exitosa")
            logger.info(f"📁 BD: {db.db_path}")
            
            tables = db.get_all_tables()
            logger.info(f"📊 Tablas: {len(tables)}")
            
            for table in tables[:5]:
                count = db.get_table_count(table)
                logger.info(f"  - {table}: {count} registros")
        else:
            logger.error("❌ Conexión fallida")
        return
    
    # Procesamiento
    pipeline = ProcessingPipeline(dry_run=dry_run, debug=debug)
    
    if file:
        # Procesar archivo único
        if not Path(file).exists():
            logger.error(f"❌ Archivo no encontrado: {file}")
            return
        
        success = pipeline.process_file(file)
        exit(0 if success else 1)
    else:
        # Procesar directorio
        pipeline.process_directory(directory)


if __name__ == '__main__':
    main()
