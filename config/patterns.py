"""
Configuración centralizada de patrones y constantes.
Reemplaza: extractor_config.py
Todos los patrones regex y configuraciones de extracción en un solo lugar.
"""

# =============================================================================
# PATRONES DE METADATOS
# =============================================================================

METADATA_PATTERNS = {
    'OT': [
        r'OT[:\s-]*(\d{3,5})',
        r'O\.?T\.?[:\s-]*(\d{3,5})',
        r'ORDEN[:\s]+TRABAJO[:\s]*(\d{3,5})',
    ],
    
    'codigo_centro': [
        r'[Cc][óo]digo\s+[Cc]entro[:\s]*(\d{6})',
        r'C[óo]d\.\s*Centro[:\s]*(\d{6})',
        r'Centro[:\s]+(\d{6})',
    ],
    
    'nombre_centro': [
        r'ID/Nombre[:\s]*([^\n]+?)(?:\s+C[óo]digo|\n|$)',
        r'Nombre\s+Centro[:\s]*([^\n]+)',
    ],
    
    'categoria': [
        r'Categor[íi]a[:\s]+(\d)',
        r'[Cc]at[:\.\s]+(\d)',
        r'CATEGORIA[:\s]+(\d)',
    ],
    
    'tipo_monitoreo': [
        r'(INFA[- ]?POST[- ]?ANAER[ÓO]BIC[OA])',
        r'(POST[- ]?ANAER[ÓO]BIC[OA])',
        r'\b(INFA)\b',
        r'\b(CPS)\b',
    ],
    
    'fecha_ingreso': [
        r'[Ff]echa\s+[Ii]ngreso\s+[Ll]aboratorio[:\s]*(\d{2}[/-]\d{2}[/-]\d{4})',
        r'[Ii]ngreso\s+[Ll]aboratorio[:\s]*(\d{2}[/-]\d{2}[/-]\d{4})',
    ],
    
    'fecha_muestreo': [
        r'[Ff]echa\s+Inicio[:/\s]*Fin[:\s]*(\d{2}[/-]\d{2}[/-]\d{4})',
        r'[Ff]echa\s+[Mm]uestreo[:\s]*(\d{2}[/-]\d{2}[/-]\d{4})',
        r'[Ff]echa\s+[Ii]nicio[:\s]*(\d{2}[/-]\d{2}[/-]\d{4})',
    ],
    
    'responsable': [
        r'Responsable\s+Terreno[:\s]*([^\n]+)',
        r'Responsable[:\s]*([^\n]+)',
    ],
}

# =============================================================================
# PATRONES DE CÓDIGOS DE MUESTRA
# =============================================================================

SAMPLE_CODE_PATTERNS = {
    'estacion_replica': r'(E\d+)-(R\d+)',  # E1-R1
    'estacion': r'E(\d+)',                  # E1
    'replica': r'R(\d+)',                   # R1
    'perfil': r'P(?:ERFIL)?\s*(\d+)',      # P1, PERFIL 1
    'transecta': r'T(?:RANSECTA)?\s*(\d+)', # T1, TRANSECTA 1
}

# =============================================================================
# KEYWORDS PARA DETECCIÓN DE TIPO DE PDF
# =============================================================================

REPORT_TYPE_KEYWORDS = {
    'SEDIMENTO': [
        'MATERIA ORGÁNICA TOTAL',
        'MATERIA ORGANICA TOTAL',
        'MOT',
        'PH/REDOX',
        'POTENCIAL REDOX',
        'ESTACIÓN',
        'RÉPLICA',
    ],
    
    'OXIGENO': [
        'PERFIL',
        'PERFILES',
        'COLUMNA DE AGUA',
        'OXÍGENO DISUELTO',
        'OXIGENO DISUELTO',
        'SATURACIÓN',
        'SALINIDAD',
    ],
    
    'VISUAL': [
        'REGISTRO VISUAL',
        'TRANSECTA',
        'CUBIERTA DE MICROORGANISMOS',
        'BURBUJAS DE GAS',
        'SUSTRATO',
        'ABUNDANCIA',
        'PHYLLUM',
    ],
}

# =============================================================================
# RANGOS DE VALIDACIÓN
# =============================================================================

VALIDATION_RANGES = {
    # Sedimento
    'MOT': (0, 100),
    'MOT_WARNING': 50,
    'pH': (0, 14),
    'pH_MARINO': (6.0, 8.5),
    'REDOX': (-500, 500),
    'TEMP_SEDIMENTO': (5, 20),
    'PESO_MUESTRA': (0.01, 15.0),
    
    # Oxígeno
    'OXIGENO': (0, 15),
    'OXIGENO_WARNING': 12,
    'SALINIDAD': (0, 40),
    'SALINIDAD_TIPICA': (28, 34),
    'SATURACION': (0, 200),
    
    # Geográficos (Chile)
    'UTM_ESTE_MIN': 166021,
    'UTM_ESTE_MAX': 833978,
    'UTM_NORTE_MIN': 1116915,
    'UTM_NORTE_MAX': 10000000,
    'PROFUNDIDAD_MAX': 300,
}

# =============================================================================
# LÍMITES REGULATORIOS (Res. Exenta 3612/09)
# =============================================================================

REGULATORY_LIMITS = {
    'INFA': {
        'MOT': 9.0,   # %
        'pH': 7.1,
        'Eh': 50,     # mV
        'OXIGENO': 2.5,  # mg/L
    },
    'INFA-POSTANAEROBICA': {
        'MOT': 8.0,
        'pH': 7.1,
        'Eh': 75,
        'OXIGENO': 3.0,
    },
    'CPS': {
        'MOT': 9.0,
        'pH': 7.1,
        'Eh': 50,
        'OXIGENO': 2.5,
    },
}

# Umbral de estaciones que deben incumplir (30% o 3 de 8)
ANAEROBIC_THRESHOLD = 0.30  # 30%
ANAEROBIC_MIN_STATIONS = 3   # Mínimo 3 estaciones

# =============================================================================
# CONFIGURACIÓN DE EXTRACCIÓN
# =============================================================================

EXTRACTION_CONFIG = {
    'CONFIANZA_MINIMA': 0.6,
    'PERMITIR_PARCIAL': True,
    'ESTRATEGIA_DUPLICADOS': 'SKIP',  # 'SKIP', 'UPDATE', 'VERSION'
    'TIMEOUT_PDF': 60,
}

# =============================================================================
# VALORES POR DEFECTO PARA DATOS CENSURADOS
# =============================================================================

DEFAULT_VALUES = {
    'CENTRO_PREFIX': 'CENS_',
    'CENTRO_NOMBRE': 'CENTRO_SIN_NOMBRE',
    'TIPO_MONITOREO': 'INFA',
    'REGION': 'SIN_ESPECIFICAR',
}
