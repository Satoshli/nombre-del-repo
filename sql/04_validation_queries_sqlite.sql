-- =============================================
-- Queries de Validación Post-Carga - SQLite
-- =============================================

.print '=============================================='
.print 'VALIDACIÓN DE INTEGRIDAD DE DATOS - SQLite'
.print '=============================================='
.print ''

-- =============================================
-- 1. CONTEO GENERAL DE REGISTROS
-- =============================================

.print '1. CONTEO GENERAL DE REGISTROS'
.print '------------------------------'

SELECT 'centros' AS Tabla, COUNT(*) AS Total FROM centros
UNION ALL
SELECT 'ordenes_trabajo', COUNT(*) FROM ordenes_trabajo
UNION ALL
SELECT 'sedimento_estaciones', COUNT(*) FROM sedimento_estaciones
UNION ALL
SELECT 'sedimento_materia_organica', COUNT(*) FROM sedimento_materia_organica
UNION ALL
SELECT 'sedimento_ph_redox', COUNT(*) FROM sedimento_ph_redox
UNION ALL
SELECT 'oxigeno_perfiles', COUNT(*) FROM oxigeno_perfiles
UNION ALL
SELECT 'oxigeno_mediciones', COUNT(*) FROM oxigeno_mediciones
UNION ALL
SELECT 'registro_visual_transectas', COUNT(*) FROM registro_visual_transectas
UNION ALL
SELECT 'registro_visual_abundancia', COUNT(*) FROM registro_visual_abundancia
UNION ALL
SELECT 'log_procesamiento', COUNT(*) FROM log_procesamiento;

.print ''

-- =============================================
-- 2. INTEGRIDAD REFERENCIAL
-- =============================================

.print '2. VERIFICACIÓN DE INTEGRIDAD REFERENCIAL'
.print '-----------------------------------------'

-- Órdenes sin centro
SELECT 'OTs sin centro' AS Verificacion, COUNT(*) AS Total
FROM ordenes_trabajo ot
LEFT JOIN centros c ON ot.centro_id = c.centro_id
WHERE c.centro_id IS NULL;

-- Estaciones sin OT
SELECT 'Estaciones sin OT' AS Verificacion, COUNT(*) AS Total
FROM sedimento_estaciones se
LEFT JOIN ordenes_trabajo ot ON se.ot_id = ot.ot_id
WHERE ot.ot_id IS NULL;

-- MOT sin estación
SELECT 'MOT sin estación' AS Verificacion, COUNT(*) AS Total
FROM sedimento_materia_organica mot
LEFT JOIN sedimento_estaciones se ON mot.estacion_id = se.estacion_id
WHERE se.estacion_id IS NULL;

.print ''

-- =============================================
-- 3. VALORES FUERA DE RANGO
-- =============================================

.print '3. VALORES FUERA DE RANGO'
.print '-------------------------'

-- MOT fuera de rango (0-100%)
SELECT 'MOT fuera de rango (0-100%)' AS Alerta, COUNT(*) AS Total
FROM sedimento_materia_organica
WHERE mot_porcentaje < 0 OR mot_porcentaje > 100;

-- MOT muy alto (>50%)
SELECT 'MOT muy alto (>50%)' AS Alerta, COUNT(*) AS Total
FROM sedimento_materia_organica
WHERE mot_porcentaje > 50;

-- pH fuera de rango marino (6.0-8.5)
SELECT 'pH fuera de rango marino (6-8.5)' AS Alerta, COUNT(*) AS Total
FROM sedimento_ph_redox
WHERE ph < 6.0 OR ph > 8.5;

-- Oxígeno muy alto (>12 mg/L)
SELECT 'Oxígeno muy alto (>12 mg/L)' AS Alerta, COUNT(*) AS Total
FROM oxigeno_mediciones
WHERE oxigeno_mg_l > 12;

-- Oxígeno crítico (<2 mg/L)
SELECT 'Oxígeno crítico (<2 mg/L)' AS Alerta, COUNT(*) AS Total
FROM oxigeno_mediciones
WHERE oxigeno_mg_l < 2;

.print ''

-- =============================================
-- 4. COMPLETITUD DE DATOS
-- =============================================

.print '4. COMPLETITUD DE DATOS'
.print '----------------------'

-- Órdenes sin fecha de muestreo
SELECT 'OTs sin fecha muestreo' AS Campo, COUNT(*) AS Total
FROM ordenes_trabajo
WHERE fecha_muestreo IS NULL;

-- Estaciones sin coordenadas
SELECT 'Estaciones sin coordenadas' AS Campo, COUNT(*) AS Total
FROM sedimento_estaciones
WHERE utm_este IS NULL OR utm_norte IS NULL;

-- MOT sin promedio calculado
SELECT 'MOT sin promedio' AS Campo, COUNT(*) AS Total
FROM sedimento_materia_organica
WHERE promedio_estacion IS NULL;

-- pH/Redox sin temperatura
SELECT 'pH/Redox sin temperatura' AS Campo, COUNT(*) AS Total
FROM sedimento_ph_redox
WHERE temperatura_c IS NULL;

.print ''

-- =============================================
-- 5. CUMPLIMIENTO REGULATORIO
-- =============================================

.print '5. ANÁLISIS DE CUMPLIMIENTO REGULATORIO'
.print '---------------------------------------'

-- Resumen por tipo de monitoreo
SELECT 
    tipo_monitoreo,
    COUNT(*) AS total_informes,
    SUM(CASE WHEN condicion_centro = 'ANAEROBICO' THEN 1 ELSE 0 END) AS anaerobicos,
    SUM(CASE WHEN condicion_centro = 'AEROBICO' THEN 1 ELSE 0 END) AS aerobicos,
    ROUND(AVG(CAST(numero_incumplimientos AS REAL)), 2) AS promedio_incumplimientos
FROM ordenes_trabajo
WHERE tipo_informe = 'SEDIMENTO'
GROUP BY tipo_monitoreo;

.print ''

-- Distribución de MOT por rango
SELECT 
    CASE 
        WHEN mot_porcentaje <= 8 THEN '0-8% (Cumple POST)'
        WHEN mot_porcentaje <= 9 THEN '8-9% (Solo cumple INFA)'
        WHEN mot_porcentaje <= 20 THEN '9-20% (Incumple)'
        WHEN mot_porcentaje <= 50 THEN '20-50% (Alto)'
        ELSE '>50% (Muy alto)'
    END AS rango_mot,
    COUNT(*) AS cantidad,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM sedimento_materia_organica), 2) AS porcentaje
FROM sedimento_materia_organica
GROUP BY 
    CASE 
        WHEN mot_porcentaje <= 8 THEN '0-8% (Cumple POST)'
        WHEN mot_porcentaje <= 9 THEN '8-9% (Solo cumple INFA)'
        WHEN mot_porcentaje <= 20 THEN '9-20% (Incumple)'
        WHEN mot_porcentaje <= 50 THEN '20-50% (Alto)'
        ELSE '>50% (Muy alto)'
    END
ORDER BY rango_mot;

.print ''

-- =============================================
-- 6. TOP INCUMPLIMIENTOS
-- =============================================

.print '6. TOP INCUMPLIMIENTOS POR CENTRO'
.print '---------------------------------'

SELECT 
    c.codigo_centro,
    c.nombre_centro,
    COUNT(DISTINCT ot.ot_id) AS num_informes,
    SUM(ot.numero_incumplimientos) AS total_incumplimientos,
    ROUND(AVG(CAST(ot.numero_incumplimientos AS REAL)), 2) AS promedio_incumplimientos,
    SUM(CASE WHEN ot.condicion_centro = 'ANAEROBICO' THEN 1 ELSE 0 END) AS veces_anaerobico
FROM centros c
INNER JOIN ordenes_trabajo ot ON c.centro_id = ot.centro_id
GROUP BY c.codigo_centro, c.nombre_centro
ORDER BY total_incumplimientos DESC
LIMIT 10;

.print ''

-- =============================================
-- 7. REGISTROS QUE REQUIEREN REVISIÓN
-- =============================================

.print '7. REGISTROS QUE REQUIEREN REVISIÓN MANUAL'
.print '------------------------------------------'

-- Centros censurados
SELECT 
    'Centros con datos censurados' AS Categoria,
    COUNT(*) AS Total
FROM centros
WHERE es_censurado = 1;

-- OTs marcadas para revisión
SELECT 
    'OTs que requieren revisión' AS Categoria,
    COUNT(*) AS Total
FROM ordenes_trabajo
WHERE requiere_revision = 1;

-- Estaciones con valores extremos
SELECT 
    'Estaciones con MOT > 30%' AS Categoria,
    COUNT(DISTINCT estacion_id) AS Total
FROM sedimento_materia_organica
WHERE mot_porcentaje > 30;

.print ''

-- =============================================
-- 8. ESTADÍSTICAS DE PROCESAMIENTO
-- =============================================

.print '8. ESTADÍSTICAS DE PROCESAMIENTO'
.print '--------------------------------'

-- Distribución de errores por nivel
SELECT 
    nivel,
    COUNT(*) AS cantidad,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM log_procesamiento), 2) AS porcentaje
FROM log_procesamiento
GROUP BY nivel
ORDER BY 
    CASE nivel
        WHEN 'ERROR' THEN 1
        WHEN 'WARNING' THEN 2
        WHEN 'INFO' THEN 3
        ELSE 4
    END;

.print ''

-- Archivos con más errores
SELECT 
    archivo_pdf,
    COUNT(*) AS num_errores
FROM log_procesamiento
WHERE nivel = 'ERROR'
GROUP BY archivo_pdf
ORDER BY num_errores DESC
LIMIT 10;

.print ''
.print '=============================================='
.print 'VALIDACIÓN COMPLETADA'
.print '=============================================='
.print ''
.print 'Revisar los resultados anteriores.'
.print 'Registros con totales > 0 requieren atención.'
