"""
Configuración general del sistema de extracción.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# =============================================
# CONFIGURACIÓN DE RUTAS
# =============================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_DIR = os.getenv('INPUT_DIR', os.path.join(BASE_DIR, 'data', 'pdfs'))
OUTPUT_DIR = os.getenv('OUTPUT_DIR', os.path.join(BASE_DIR, 'data', 'processed'))
LOG_DIR = os.path.join(BASE_DIR, 'logs')
DATA_DIR = os.path.join(BASE_DIR, 'data')

# Base de datos SQLite
DB_PATH = os.getenv('DB_PATH', os.path.join(DATA_DIR, 'monitoreo_ambiental.db'))

# Crear directorios si no existen
for directory in [INPUT_DIR, OUTPUT_DIR, LOG_DIR, DATA_DIR]:
    os.makedirs(directory, exist_ok=True)

# =============================================
# CONFIGURACIÓN DE LOGGING
# =============================================

LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = os.path.join(LOG_DIR, 'procesamiento.log')
LOG_FORMAT = '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# =============================================
# VALORES POR DEFECTO PARA DATOS CENSURADOS
# =============================================

DEFAULT_VALUES = {
    'CENTRO_PREFIX': 'CENS_',  # Prefijo para centros censurados
    'CENTRO_CODIGO': 'CENTRO_UNKNOWN',
    'CENTRO_NOMBRE': 'CENTRO_SIN_NOMBRE',
    'REGION': 'SIN_ESPECIFICAR',
    'TIPO_MONITOREO': 'INFA',  # Asumir INFA por defecto
}

# =============================================
# LÍMITES REGULATORIOS (Res. Exenta 3612/09)
# =============================================

LIMITES_INFA = {
    'MOT_MAX': 9.0,  # %
    'PH_MIN': 7.1,
    'REDOX_MIN': 50.0,  # mV (EH)
    'OXIGENO_MIN': 2.5,  # mg/L (Z-1)
}

LIMITES_INFA_POST = {
    'MOT_MAX': 8.0,  # %
    'PH_MIN': 7.1,
    'REDOX_MIN': 75.0,  # mV (EH)
    'OXIGENO_MIN': 3.0,  # mg/L (Z-1)
}

# Porcentaje de estaciones que deben incumplir para marcar centro como anaeróbico
UMBRAL_ANAEROBICO = {
    'SEDIMENTO': 0.375,  # 3 de 8 estaciones (37.5%)
    'OXIGENO': 0.30,     # 30% de perfiles
    'VISUAL': 0.25,      # 2 de 8 transectas
}

# =============================================
# RANGOS DE VALIDACIÓN
# =============================================

RANGOS_VALIDOS = {
    # Sedimento
    'MOT': (0, 100),  # % (WARNING si >50)
    'MOT_WARNING': 50,
    'PH': (0, 14),
    'PH_MARINO': (6.0, 8.5),  # Rango típico
    'REDOX': (-500, 500),  # mV
    'TEMP_SEDIMENTO': (5, 20),  # °C
    'PESO_MUESTRA': (0.01, 15.0),  # gramos
    
    # Oxígeno
    'OXIGENO': (0, 15),  # mg/L
    'OXIGENO_WARNING': 12,  # >12 es raro pero posible
    'TEMP_AGUA': (5, 20),  # °C
    'SALINIDAD': (0, 40),  # PSU
    'SALINIDAD_CHILE': (28, 34),  # Rango típico Chile
    'SATURACION': (0, 200),  # %
    
    # Geográficos
    'UTM_ESTE_MIN': 166021,
    'UTM_ESTE_MAX': 833978,
    'UTM_NORTE_MIN': 1116915,
    'UTM_NORTE_MAX': 10000000,
    'PROFUNDIDAD_MIN': 1,
    'PROFUNDIDAD_MAX': 300,  # metros
    'PROFUNDIDAD_TIPICA_MAX': 100,  # Típico en acuicultura
    
    # Mediciones
    'NUM_ESTACIONES_MIN': 1,
    'NUM_ESTACIONES_MAX': 20,
    'NUM_ESTACIONES_TIPICO': 8,
    'NUM_REPLICAS_MIN': 1,
    'NUM_REPLICAS_MAX': 10,
    'NUM_REPLICAS_TIPICO': 3,
}

# =============================================
# CÓDIGOS DE ABUNDANCIA (Registro Visual)
# =============================================

ABUNDANCIA_CODIGOS = {
    'R': {'nombre': 'Raro', 'min': 1, 'max': 2},
    'E': {'nombre': 'Escaso', 'min': 3, 'max': 5},
    'M': {'nombre': 'Moderado', 'min': 6, 'max': 10},
    'A': {'nombre': 'Abundante', 'min': 11, 'max': 20},
    'MA': {'nombre': 'Muy Abundante', 'min': 21, 'max': None},
    '-': {'nombre': 'Ausente', 'min': 0, 'max': 0},
}

SUSTRATOS_VALIDOS = ['Duro', 'Blando', 'Mixto']

# =============================================
# CONFIGURACIÓN DE EXTRACCIÓN
# =============================================

EXTRACCION_CONFIG = {
    # Estrategia de fallback para parsing
    'PARSE_STRATEGY': ['pdfplumber', 'tabula', 'camelot'],
    
    # Umbral de confianza mínimo (0-1)
    'CONFIANZA_MINIMA': 0.6,
    
    # Permitir extracción parcial
    'PERMITIR_PARCIAL': True,
    
    # Estrategia para duplicados
    'ESTRATEGIA_DUPLICADOS': 'SKIP',  # 'SKIP', 'UPDATE', 'VERSION'
    
    # Timeout para procesamiento de PDF (segundos)
    'TIMEOUT_PDF': 60,
    
    # Número de workers para procesamiento paralelo
    'NUM_WORKERS': max(1, os.cpu_count() - 1) if os.cpu_count() else 1,
}

# =============================================
# PATTERNS REGEX
# =============================================

REGEX_PATTERNS = {
    # Código OT: "OT 1319", "O 2112", "OT-1464", "OT:2465"
    'CODIGO_OT': r'O[T]?\s*[:-]?\s*(\d{3,5})',
    
    # Estación: "E1-R1", "E1R1", "E10-R2"
    'ESTACION': r'E(\d+)-?R(\d+)',
    
    # Perfil: "P1", "P2", "PERFIL 3"
    'PERFIL': r'P(?:ERFIL)?\s*(\d+)',
    
    # Transecta: "T1", "T2-R1", "TRANSECTA 3"
    'TRANSECTA': r'T(?:RANSECTA)?\s*(\d+)',
    
    # UTM: capturas Este y Norte
    'UTM': r'(\d{6,7})\s+(\d{7})',
    
    # Fechas: DD-MM-YYYY, DD/MM/YYYY, YYYY-MM-DD
    'FECHA': r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})|(\d{4})[/-](\d{1,2})[/-](\d{1,2})',
    
    # Hora: HH:MM, HH:MM:SS
    'HORA': r'(\d{1,2}):(\d{2})(?::(\d{2}))?',
    
    # Número decimal (acepta coma y punto)
    'DECIMAL': r'[-+]?\d+[,.]?\d*',
}

# =============================================
# KEYWORDS PARA BÚSQUEDA EN PDFs
# =============================================

KEYWORDS = {
    'TIPO_INFORME': {
        'SEDIMENTO': ['MATERIA ORGÁNICA', 'MOT', 'PH/REDOX', 'POTENCIAL REDOX'],
        'OXIGENO': ['OXÍGENO DISUELTO', 'PERFIL', 'COLUMNA DE AGUA', 'SATURACIÓN'],
        'VISUAL': ['REGISTRO VISUAL', 'TRANSECTA', 'FILMACIÓN', 'SUSTRATO'],
    },
    'TIPO_MONITOREO': {
        'INFA': ['INFA', 'INFORME AMBIENTAL'],
        'INFA-POSTANAEROBICA': ['POST-ANAERÓBICA', 'POSTANAERÓBICA', 'POST ANAERÓBICA'],
        'CPS': ['CPS', 'CENTRO PREVIO A SIEMBRA'],
    },
    'TABLAS': {
        'UBICACION': ['UBICACIÓN', 'IDENTIFICACIÓN', 'ESTACIÓN', 'UTM'],
        'MOT': ['MATERIA ORGÁNICA TOTAL', 'MOT'],
        'PH_REDOX': ['PH/REDOX', 'POTENCIAL REDOX', 'PH', 'REDOX'],
        'OXIGENO': ['OXÍGENO DISUELTO', 'PERFIL', 'COLUMNA'],
        'VISUAL': ['REGISTRO VISUAL', 'TRANSECTA'],
        'ABUNDANCIA': ['ABUNDANCIA', 'PHYLLUM', 'PHYLUM', 'TAXA'],
    },
}

# =============================================
# CONFIGURACIÓN DE AUDITORÍA
# =============================================

AUDITORIA_CONFIG = {
    # Registros esperados por tabla según tipo de informe
    'REGISTROS_ESPERADOS': {
        'SEDIMENTO': {
            'sedimento_estaciones': 8,  # Típico, puede variar
            'sedimento_materia_organica': 24,  # 8 estaciones x 3 réplicas
            'sedimento_ph_redox': 24,
        },
        'OXIGENO': {
            'oxigeno_perfiles': 8,
            'oxigeno_mediciones': 80,  # Variable según profundidad
        },
        'VISUAL': {
            'registro_visual_transectas': 8,
            'registro_visual_abundancia': 40,  # Variable
        },
    },
    
    # Umbral de completitud para marcar revisión (%)
    'UMBRAL_COMPLETITUD': 80,
    
    # Umbral de valores fuera de rango (%)
    'UMBRAL_OUTLIERS': 10,
}

# =============================================
# MENSAJES DE ERROR Y WARNING
# =============================================

MENSAJES = {
    'ERROR': {
        'NO_OT': 'No se pudo extraer código OT del PDF',
        'NO_TABLA': 'No se encontró tabla requerida: {}',
        'TABLA_VACIA': 'Tabla {} está vacía o mal formateada',
        'CONEXION_DB': 'Error de conexión a base de datos',
        'DUPLICADO': 'Código OT {} ya existe en la base de datos',
    },
    'WARNING': {
        'MOT_ALTO': 'MOT = {:.2f}% está por encima de lo normal (>50%)',
        'COORDENADAS': 'Coordenadas UTM parecen estar intercambiadas',
        'FECHA_FUTURA': 'Fecha de muestreo es futura: {}',
        'EXTRACCION_PARCIAL': 'Extracción parcial: {} de {} registros',
        'CENSURADO': 'Datos censurados detectados en {}',
    },
    'INFO': {
        'INICIO_PROCESO': 'Iniciando procesamiento de {}',
        'FIN_PROCESO': 'Procesamiento completado: {} en {:.2f} segundos',
        'CARGA_EXITOSA': 'Datos cargados exitosamente: {} registros en {}',
    },
}
