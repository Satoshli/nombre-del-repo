-- =============================================
-- Sistema de Base de Datos para Monitoreo Ambiental Acuícola
-- SQLite 3
-- Fecha: 2024-01
-- =============================================

-- =============================================
-- CAPA 1: METADATOS
-- =============================================

-- Tabla de Centros de Cultivo
DROP TABLE IF EXISTS centros;
CREATE TABLE centros (
    centro_id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo_centro TEXT UNIQUE NOT NULL,
    nombre_centro TEXT DEFAULT 'CENTRO_SIN_NOMBRE',
    categoria INTEGER CHECK (categoria BETWEEN 1 AND 5),
    ubicacion_region TEXT,
    utm_este REAL CHECK (utm_este BETWEEN 166021 AND 833978 OR utm_este IS NULL),
    utm_norte REAL CHECK (utm_norte BETWEEN 1116915 AND 10000000 OR utm_norte IS NULL),
    es_censurado INTEGER DEFAULT 0 CHECK (es_censurado IN (0, 1)),
    fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP,
    CHECK (utm_norte > utm_este OR (utm_este IS NULL AND utm_norte IS NULL))
);

CREATE INDEX idx_centros_codigo ON centros(codigo_centro);
CREATE INDEX idx_centros_region ON centros(ubicacion_region);

-- Tabla de Órdenes de Trabajo
DROP TABLE IF EXISTS ordenes_trabajo;
CREATE TABLE ordenes_trabajo (
    ot_id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo_ot TEXT UNIQUE NOT NULL,
    centro_id INTEGER REFERENCES centros(centro_id) ON DELETE CASCADE,
    tipo_informe TEXT CHECK (tipo_informe IN ('SEDIMENTO', 'OXIGENO', 'VISUAL', 'MIXTO')),
    tipo_monitoreo TEXT CHECK (tipo_monitoreo IN ('INFA', 'INFA-POSTANAEROBICA', 'CPS')),
    fecha_muestreo DATE,
    condicion_centro TEXT CHECK (condicion_centro IN ('AEROBICO', 'ANAEROBICO')),
    numero_incumplimientos INTEGER DEFAULT 0 CHECK (numero_incumplimientos >= 0),
    requiere_revision INTEGER DEFAULT 0 CHECK (requiere_revision IN (0, 1)),
    archivo_pdf_original TEXT,
    fecha_procesamiento DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_ordenes_codigo ON ordenes_trabajo(codigo_ot);
CREATE INDEX idx_ordenes_fecha ON ordenes_trabajo(fecha_muestreo);
CREATE INDEX idx_ordenes_tipo ON ordenes_trabajo(tipo_informe);
CREATE INDEX idx_ordenes_centro ON ordenes_trabajo(centro_id);
CREATE INDEX idx_ordenes_revision ON ordenes_trabajo(requiere_revision);

-- =============================================
-- CAPA 2: DATOS DE MEDICIONES - SEDIMENTO
-- =============================================

-- Tabla de Estaciones de Sedimento
DROP TABLE IF EXISTS sedimento_estaciones;
CREATE TABLE sedimento_estaciones (
    estacion_id INTEGER PRIMARY KEY AUTOINCREMENT,
    ot_id INTEGER NOT NULL REFERENCES ordenes_trabajo(ot_id) ON DELETE CASCADE,
    codigo_estacion TEXT NOT NULL,
    utm_este REAL CHECK (utm_este BETWEEN 166021 AND 833978 OR utm_este IS NULL),
    utm_norte REAL CHECK (utm_norte BETWEEN 1116915 AND 10000000 OR utm_norte IS NULL),
    profundidad_m REAL CHECK (profundidad_m > 0 AND profundidad_m < 300 OR profundidad_m IS NULL),
    UNIQUE(ot_id, codigo_estacion)
);

CREATE INDEX idx_sedimento_estaciones_ot ON sedimento_estaciones(ot_id);
CREATE INDEX idx_sedimento_estaciones_codigo ON sedimento_estaciones(codigo_estacion);

-- Tabla de Materia Orgánica Total
DROP TABLE IF EXISTS sedimento_materia_organica;
CREATE TABLE sedimento_materia_organica (
    mot_id INTEGER PRIMARY KEY AUTOINCREMENT,
    estacion_id INTEGER NOT NULL REFERENCES sedimento_estaciones(estacion_id) ON DELETE CASCADE,
    codigo_muestra TEXT NOT NULL,
    replica INTEGER CHECK (replica BETWEEN 1 AND 10),
    peso_muestra_g REAL CHECK (peso_muestra_g > 0 OR peso_muestra_g IS NULL),
    mot_porcentaje REAL CHECK (mot_porcentaje BETWEEN 0 AND 100),
    promedio_estacion REAL,
    cumple_limite_infa INTEGER CHECK (cumple_limite_infa IN (0, 1)),
    cumple_limite_post INTEGER CHECK (cumple_limite_post IN (0, 1))
);

CREATE INDEX idx_mot_estacion ON sedimento_materia_organica(estacion_id);
CREATE INDEX idx_mot_codigo ON sedimento_materia_organica(codigo_muestra);
CREATE INDEX idx_mot_cumplimiento ON sedimento_materia_organica(cumple_limite_infa, cumple_limite_post);

-- Tabla de pH y Redox
DROP TABLE IF EXISTS sedimento_ph_redox;
CREATE TABLE sedimento_ph_redox (
    ph_redox_id INTEGER PRIMARY KEY AUTOINCREMENT,
    estacion_id INTEGER NOT NULL REFERENCES sedimento_estaciones(estacion_id) ON DELETE CASCADE,
    codigo_muestra TEXT NOT NULL,
    replica INTEGER CHECK (replica BETWEEN 1 AND 10),
    ph REAL CHECK (ph BETWEEN 0 AND 14 OR ph IS NULL),
    promedio_ph REAL,
    potencial_redox_mv REAL CHECK (potencial_redox_mv BETWEEN -500 AND 500 OR potencial_redox_mv IS NULL),
    promedio_redox REAL,
    temperatura_c REAL CHECK (temperatura_c BETWEEN 5 AND 20 OR temperatura_c IS NULL),
    cumple_ph INTEGER CHECK (cumple_ph IN (0, 1)),
    cumple_redox INTEGER CHECK (cumple_redox IN (0, 1)),
    cumple_conjunto INTEGER CHECK (cumple_conjunto IN (0, 1))
);

CREATE INDEX idx_ph_redox_estacion ON sedimento_ph_redox(estacion_id);
CREATE INDEX idx_ph_redox_cumplimiento ON sedimento_ph_redox(cumple_conjunto);

-- =============================================
-- CAPA 2: DATOS DE MEDICIONES - OXÍGENO
-- =============================================

-- Tabla de Perfiles de Oxígeno
DROP TABLE IF EXISTS oxigeno_perfiles;
CREATE TABLE oxigeno_perfiles (
    perfil_id INTEGER PRIMARY KEY AUTOINCREMENT,
    ot_id INTEGER NOT NULL REFERENCES ordenes_trabajo(ot_id) ON DELETE CASCADE,
    codigo_perfil TEXT NOT NULL,
    profundidad_maxima_m REAL CHECK (profundidad_maxima_m > 0 AND profundidad_maxima_m < 300 OR profundidad_maxima_m IS NULL),
    utm_este REAL CHECK (utm_este BETWEEN 166021 AND 833978 OR utm_este IS NULL),
    utm_norte REAL CHECK (utm_norte BETWEEN 1116915 AND 10000000 OR utm_norte IS NULL),
    UNIQUE(ot_id, codigo_perfil)
);

CREATE INDEX idx_oxigeno_perfiles_ot ON oxigeno_perfiles(ot_id);

-- Tabla de Mediciones de Oxígeno
DROP TABLE IF EXISTS oxigeno_mediciones;
CREATE TABLE oxigeno_mediciones (
    medicion_id INTEGER PRIMARY KEY AUTOINCREMENT,
    perfil_id INTEGER NOT NULL REFERENCES oxigeno_perfiles(perfil_id) ON DELETE CASCADE,
    capa INTEGER CHECK (capa > 0),
    profundidad_m REAL CHECK (profundidad_m >= 0),
    es_z_menos_1 INTEGER DEFAULT 0 CHECK (es_z_menos_1 IN (0, 1)),
    oxigeno_mg_l REAL CHECK (oxigeno_mg_l BETWEEN 0 AND 15 OR oxigeno_mg_l IS NULL),
    temperatura_c REAL CHECK (temperatura_c BETWEEN 5 AND 20 OR temperatura_c IS NULL),
    salinidad_psu REAL CHECK (salinidad_psu BETWEEN 0 AND 40 OR salinidad_psu IS NULL),
    saturacion_pct REAL CHECK (saturacion_pct BETWEEN 0 AND 200 OR saturacion_pct IS NULL),
    cumple_limite INTEGER CHECK (cumple_limite IN (0, 1))
);

CREATE INDEX idx_oxigeno_mediciones_perfil ON oxigeno_mediciones(perfil_id);
CREATE INDEX idx_oxigeno_z1 ON oxigeno_mediciones(es_z_menos_1) WHERE es_z_menos_1 = 1;
CREATE INDEX idx_oxigeno_cumplimiento ON oxigeno_mediciones(cumple_limite);

-- =============================================
-- CAPA 2: DATOS DE MEDICIONES - REGISTRO VISUAL
-- =============================================

-- Tabla de Transectas
DROP TABLE IF EXISTS registro_visual_transectas;
CREATE TABLE registro_visual_transectas (
    transecta_id INTEGER PRIMARY KEY AUTOINCREMENT,
    ot_id INTEGER NOT NULL REFERENCES ordenes_trabajo(ot_id) ON DELETE CASCADE,
    codigo_transecta TEXT NOT NULL,
    fecha_filmacion DATE,
    hora_inicio TIME,
    hora_fin TIME,
    tipo_sustrato TEXT CHECK (tipo_sustrato IN ('Duro', 'Blando', 'Mixto') OR tipo_sustrato IS NULL),
    hay_cubierta_microbiana INTEGER DEFAULT 0 CHECK (hay_cubierta_microbiana IN (0, 1)),
    hay_burbujas_gas INTEGER DEFAULT 0 CHECK (hay_burbujas_gas IN (0, 1)),
    observaciones TEXT,
    UNIQUE(ot_id, codigo_transecta)
);

CREATE INDEX idx_visual_transectas_ot ON registro_visual_transectas(ot_id);
CREATE INDEX idx_visual_cubierta ON registro_visual_transectas(hay_cubierta_microbiana);

-- Tabla de Abundancia de Especies
DROP TABLE IF EXISTS registro_visual_abundancia;
CREATE TABLE registro_visual_abundancia (
    abundancia_id INTEGER PRIMARY KEY AUTOINCREMENT,
    transecta_id INTEGER NOT NULL REFERENCES registro_visual_transectas(transecta_id) ON DELETE CASCADE,
    grupo_taxonomico TEXT,
    especie TEXT,
    abundancia TEXT CHECK (abundancia IN ('R', 'E', 'M', 'A', 'MA', '-') OR abundancia IS NULL),
    individuos_min INTEGER,
    individuos_max INTEGER
);

CREATE INDEX idx_visual_abundancia_transecta ON registro_visual_abundancia(transecta_id);
CREATE INDEX idx_visual_especie ON registro_visual_abundancia(especie);

-- =============================================
-- CAPA 3: CONTROL Y AUDITORÍA
-- =============================================

-- Tabla de Auditoría de Extracción
DROP TABLE IF EXISTS auditoria_extraccion;
CREATE TABLE auditoria_extraccion (
    auditoria_id INTEGER PRIMARY KEY AUTOINCREMENT,
    ot_id INTEGER REFERENCES ordenes_trabajo(ot_id) ON DELETE CASCADE,
    tabla_afectada TEXT,
    registros_esperados INTEGER,
    registros_extraidos INTEGER,
    porcentaje_completitud REAL,
    valores_fuera_rango INTEGER DEFAULT 0,
    tiempo_procesamiento_seg REAL,
    requiere_revision INTEGER DEFAULT 0 CHECK (requiere_revision IN (0, 1)),
    fecha_auditoria DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_auditoria_ot ON auditoria_extraccion(ot_id);
CREATE INDEX idx_auditoria_revision ON auditoria_extraccion(requiere_revision);

-- Tabla de Log de Procesamiento
DROP TABLE IF EXISTS log_procesamiento;
CREATE TABLE log_procesamiento (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    archivo_pdf TEXT,
    nivel TEXT CHECK (nivel IN ('INFO', 'WARNING', 'ERROR', 'DEBUG')),
    fase TEXT,
    mensaje TEXT
);

CREATE INDEX idx_log_timestamp ON log_procesamiento(timestamp);
CREATE INDEX idx_log_nivel ON log_procesamiento(nivel);
CREATE INDEX idx_log_archivo ON log_procesamiento(archivo_pdf);

-- =============================================
-- TABLA DE CONFIGURACIÓN PARA VALORES POR DEFECTO
-- =============================================

DROP TABLE IF EXISTS config_valores_default;
CREATE TABLE config_valores_default (
    config_id INTEGER PRIMARY KEY AUTOINCREMENT,
    parametro TEXT UNIQUE NOT NULL,
    valor_default TEXT,
    descripcion TEXT,
    fecha_actualizacion DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Insertar valores por defecto para datos censurados
INSERT INTO config_valores_default (parametro, valor_default, descripcion) VALUES
('CENTRO_SIN_CODIGO', 'CENTRO_UNKNOWN', 'Código por defecto cuando no se puede extraer del PDF'),
('CENTRO_SIN_NOMBRE', 'CENTRO_SIN_NOMBRE', 'Nombre por defecto para centros censurados'),
('REGION_DEFAULT', 'SIN_ESPECIFICAR', 'Región por defecto cuando no está disponible'),
('TIPO_MONITOREO_DEFAULT', 'INFA', 'Tipo de monitoreo por defecto si no se detecta'),
('PREFIX_CENSURADO', 'CENS_', 'Prefijo para identificar centros con datos censurados');

-- Verificación final
SELECT 'Schema SQLite creado exitosamente' AS status;
SELECT COUNT(*) || ' tablas creadas' AS info FROM sqlite_master WHERE type='table';
SELECT COUNT(*) || ' índices creados' AS info FROM sqlite_master WHERE type='index';
