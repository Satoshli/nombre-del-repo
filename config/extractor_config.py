"""
Configuración de patrones de extracción.
Permite ajustar patrones sin modificar código.
"""

# Patrones para metadatos (múltiples opciones por prioridad)
METADATA_PATTERNS = {
    'OT': [
        r'OT[:\s-]*(\d{3,5})',
        r'O\.?T\.?[:\s-]*(\d{3,5})',
        r'ORDEN[:\s]+TRABAJO[:\s]*(\d{3,5})',
    ],
    
    'CODIGO_CENTRO': [
        r'[Cc][óo]digo\s+[Cc]entro[:\s]*(\d{6})',
        r'C[óo]d\.\s*Centro[:\s]*(\d{6})',
        r'Centro[:\s]+(\d{6})',
        r'ID[:\s]*(\d{6})',
    ],
    
    'CATEGORIA': [
        r'[Cc]at\.?\s*(\d)',  # "cat. 5" - MÁS ESPECÍFICO PRIMERO
        r'[Cc]ategor[íi]a[:\s]*[Cc]at\.?\s*(\d)',
        r'[Cc]ategor[íi]a[:\s]*(\d)',
        r'CATEGORIA[:\s]*(\d)',
    ],
    
    'TIPO_MONITOREO': [
        r'(INFA[- ]?POST[- ]?ANAER[ÓO]BIC[OA])',  # MÁS ESPECÍFICO
        r'(POST[- ]?ANAER[ÓO]BIC[OA])',
        r'(INFA)',
        r'(CPS)',
        r'[Tt]ipo\s+de\s+[Mm]onitoreo[:\s]*([^\n]+)',
    ],
    
    'FECHA_INGRESO': [
        r'[Ff]echa\s+[Ii]ngreso\s+[Ll]aboratorio[:\s]*(\d{2}[/-]\d{2}[/-]\d{4})',
        r'[Ff]echa\s+[Ii]ngreso[:\s]*(\d{2}[/-]\d{2}[/-]\d{4})',
        r'[Ii]ngreso[:\s]+[Mm]uestras[:\s]*(\d{2}[/-]\d{2}[/-]\d{4})',
    ],
    
    'FECHA_MUESTREO': [
        r'[Ff]echa\s+[Mm]uestreo[:\s]*(\d{2}[/-]\d{2}[/-]\d{4})',
        r'[Ff]echa\s+[Ii]nicio[:\s]*(\d{2}[/-]\d{2}[/-]\d{4})',
        r'[Mm]uestreo[:\s]*(\d{2}[/-]\d{2}[/-]\d{4})',
    ],
    
    'CONDICION_CENTRO': [
        r'[Cc]ondici[óo]n[:\s]*([Aa]naer[óo]bic[oa]|[Aa]er[óo]bic[oa])',
        r'[Ee]stado[:\s]*([Aa]naer[óo]bic[oa]|[Aa]er[óo]bic[oa])',
        r'[Rr]esultado[:\s]*([Aa]naer[óo]bic[oa]|[Aa]er[óo]bic[oa])',
        r'[Pp]resenta\s+estado\s+([Aa]naer[óo]bic[oa])',
        r'[Cc]entro\s+([Aa]naer[óo]bic[oa]|[Aa]er[óo]bic[oa])',
    ],
    
    'NOMBRE_CENTRO': [
        r'ID/Nombre[:\s]*([^\n]+)',
        r'Nombre\s+Centro[:\s]*([^\n]+)',
        r'Centro[:\s]*([A-Za-zÀ-ÿ\s]+)',
    ],
}

# Keywords para detección de tipo de PDF
TIPO_PDF_KEYWORDS = {
    'SEDIMENTO': [
        'MATERIA ORGÁNICA TOTAL',
        'MATERIA ORGANICA TOTAL',
        'MOT',
        'PH/REDOX',
        'POTENCIAL REDOX',
        'ESTACIÓN',
        'ESTACION',
        'RÉPLICA',
        'REPLICA',
    ],
    
    'OXIGENO': [
        'PERFIL',
        'PERFILES',
        'COLUMNA DE AGUA',
        'OXÍGENO DISUELTO',
        'OXIGENO DISUELTO',
        'SATURACIÓN',
        'SATURACION',
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
        'PHYLUM',
    ],
}

# Patrones para códigos de muestreo
CODIGO_PATTERNS = {
    'ESTACION': r'(E\d+)-?R\d+',           # E1-R1, E1R1
    'ESTACION_REPLICA': r'(E\d+)-(R\d+)',  # E1-R1
    'PERFIL': r'P(?:ERFIL)?\s*(\d+)',      # P1, PERFIL 1
    'TRANSECTA': r'T(?:RANSECTA)?\s*(\d+)', # T1, TRANSECTA 1
}

# Campos obligatorios para validación
METADATOS_OBLIGATORIOS = [
    'codigo_ot',
    'codigo_centro',
    'categoria',
    'tipo_monitoreo',
    'fecha_ingreso',
    'condicion_centro',
]

# Rangos de validación
RANGOS_VALIDACION = {
    'MOT': (0, 100),
    'MOT_WARNING': 50,
    'PH': (0, 14),
    'PH_MARINO': (6.0, 8.5),
    'REDOX': (-500, 500),
    'TEMP_SEDIMENTO': (5, 20),
    'PESO_MUESTRA': (0.01, 15.0),
    'CATEGORIA': (1, 5),
}
