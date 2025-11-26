-- =============================================
-- Vistas para Power BI y Análisis
-- =============================================

USE MonitoreoAmbiental;
GO

-- =============================================
-- VISTA: Resumen de Órdenes de Trabajo
-- =============================================

CREATE OR ALTER VIEW vw_resumen_ordenes AS
SELECT 
    ot.ot_id,
    ot.codigo_ot,
    c.codigo_centro,
    c.nombre_centro,
    c.categoria,
    c.ubicacion_region,
    c.es_censurado,
    ot.tipo_informe,
    ot.tipo_monitoreo,
    ot.fecha_muestreo,
    YEAR(ot.fecha_muestreo) AS anio_muestreo,
    MONTH(ot.fecha_muestreo) AS mes_muestreo,
    ot.condicion_centro,
    ot.numero_incumplimientos,
    ot.requiere_revision,
    ot.archivo_pdf_original,
    ot.fecha_procesamiento,
    DATEDIFF(DAY, ot.fecha_procesamiento, GETDATE()) AS dias_desde_procesamiento
FROM dbo.ordenes_trabajo ot
LEFT JOIN dbo.centros c ON ot.centro_id = c.centro_id;
GO

-- =============================================
-- VISTA: Análisis de Sedimento Completo
-- =============================================

CREATE OR ALTER VIEW vw_analisis_sedimento AS
SELECT 
    ot.codigo_ot,
    c.codigo_centro,
    c.nombre_centro,
    ot.fecha_muestreo,
    ot.tipo_monitoreo,
    se.codigo_estacion,
    se.profundidad_m,
    se.utm_este,
    se.utm_norte,
    mot.codigo_muestra,
    mot.replica,
    mot.mot_porcentaje,
    mot.promedio_estacion AS mot_promedio,
    mot.cumple_limite_infa AS mot_cumple_infa,
    mot.cumple_limite_post AS mot_cumple_post,
    pr.ph,
    pr.promedio_ph AS ph_promedio,
    pr.potencial_redox_mv AS redox_eh,
    pr.promedio_redox AS redox_promedio,
    pr.temperatura_c,
    pr.cumple_ph,
    pr.cumple_redox,
    pr.cumple_conjunto AS cumple_ph_redox_conjunto,
    CASE 
        WHEN ot.tipo_monitoreo = 'INFA' THEN 
            CASE WHEN mot.mot_porcentaje <= 9 THEN 'CUMPLE' ELSE 'NO_CUMPLE' END
        WHEN ot.tipo_monitoreo = 'INFA-POSTANAEROBICA' THEN
            CASE WHEN mot.mot_porcentaje <= 8 THEN 'CUMPLE' ELSE 'NO_CUMPLE' END
        ELSE 'N/A'
    END AS estado_mot,
    CASE 
        WHEN pr.cumple_conjunto = 1 THEN 'CUMPLE'
        WHEN pr.cumple_conjunto = 0 THEN 'NO_CUMPLE'
        ELSE 'N/A'
    END AS estado_ph_redox
FROM dbo.ordenes_trabajo ot
INNER JOIN dbo.centros c ON ot.centro_id = c.centro_id
INNER JOIN dbo.sedimento_estaciones se ON ot.ot_id = se.ot_id
LEFT JOIN dbo.sedimento_materia_organica mot ON se.estacion_id = mot.estacion_id
LEFT JOIN dbo.sedimento_ph_redox pr ON se.estacion_id = pr.estacion_id 
    AND mot.replica = pr.replica;
GO

-- =============================================
-- VISTA: Análisis de Oxígeno Disuelto
-- =============================================

CREATE OR ALTER VIEW vw_analisis_oxigeno AS
SELECT 
    ot.codigo_ot,
    c.codigo_centro,
    c.nombre_centro,
    ot.fecha_muestreo,
    ot.tipo_monitoreo,
    op.codigo_perfil,
    op.profundidad_maxima_m,
    om.capa,
    om.profundidad_m,
    om.es_z_menos_1,
    om.oxigeno_mg_l,
    om.temperatura_c,
    om.salinidad_psu,
    om.saturacion_pct,
    om.cumple_limite,
    CASE 
        WHEN ot.tipo_monitoreo = 'INFA' THEN 2.5
        WHEN ot.tipo_monitoreo = 'INFA-POSTANAEROBICA' THEN 3.0
        ELSE NULL
    END AS limite_aplicable,
    CASE 
        WHEN om.cumple_limite = 1 THEN 'CUMPLE'
        WHEN om.cumple_limite = 0 THEN 'NO_CUMPLE'
        ELSE 'N/A'
    END AS estado_oxigeno,
    CASE 
        WHEN om.oxigeno_mg_l < 2.0 THEN 'CRITICO'
        WHEN om.oxigeno_mg_l BETWEEN 2.0 AND 3.0 THEN 'BAJO'
        WHEN om.oxigeno_mg_l BETWEEN 3.0 AND 5.0 THEN 'MODERADO'
        WHEN om.oxigeno_mg_l > 5.0 THEN 'BUENO'
        ELSE 'N/A'
    END AS clasificacion_oxigeno
FROM dbo.ordenes_trabajo ot
INNER JOIN dbo.centros c ON ot.centro_id = c.centro_id
INNER JOIN dbo.oxigeno_perfiles op ON ot.ot_id = op.ot_id
INNER JOIN dbo.oxigeno_mediciones om ON op.perfil_id = om.perfil_id;
GO

-- =============================================
-- VISTA: Mediciones Críticas Z-1
-- =============================================

CREATE OR ALTER VIEW vw_oxigeno_z1_critico AS
SELECT 
    ot.codigo_ot,
    c.codigo_centro,
    c.nombre_centro,
    ot.fecha_muestreo,
    ot.tipo_monitoreo,
    op.codigo_perfil,
    om.oxigeno_mg_l,
    om.temperatura_c,
    om.salinidad_psu,
    om.cumple_limite,
    CASE 
        WHEN ot.tipo_monitoreo = 'INFA' THEN 2.5
        WHEN ot.tipo_monitoreo = 'INFA-POSTANAEROBICA' THEN 3.0
    END AS limite_requerido,
    om.oxigeno_mg_l - CASE 
        WHEN ot.tipo_monitoreo = 'INFA' THEN 2.5
        WHEN ot.tipo_monitoreo = 'INFA-POSTANAEROBICA' THEN 3.0
    END AS diferencia_limite
FROM dbo.ordenes_trabajo ot
INNER JOIN dbo.centros c ON ot.centro_id = c.centro_id
INNER JOIN dbo.oxigeno_perfiles op ON ot.ot_id = op.ot_id
INNER JOIN dbo.oxigeno_mediciones om ON op.perfil_id = om.perfil_id
WHERE om.es_z_menos_1 = 1;
GO

-- =============================================
-- VISTA: Registro Visual y Biodiversidad
-- =============================================

CREATE OR ALTER VIEW vw_biodiversidad AS
SELECT 
    ot.codigo_ot,
    c.codigo_centro,
    c.nombre_centro,
    ot.fecha_muestreo,
    rt.codigo_transecta,
    rt.tipo_sustrato,
    rt.hay_cubierta_microbiana,
    rt.hay_burbujas_gas,
    ab.grupo_taxonomico,
    ab.especie,
    ab.abundancia,
    ab.individuos_min,
    ab.individuos_max,
    CASE ab.abundancia
        WHEN 'R' THEN 'Raro (1-2)'
        WHEN 'E' THEN 'Escaso (3-5)'
        WHEN 'M' THEN 'Moderado (6-10)'
        WHEN 'A' THEN 'Abundante (11-20)'
        WHEN 'MA' THEN 'Muy Abundante (20+)'
        WHEN '-' THEN 'Ausente'
        ELSE 'No Determinado'
    END AS descripcion_abundancia
FROM dbo.ordenes_trabajo ot
INNER JOIN dbo.centros c ON ot.centro_id = c.centro_id
INNER JOIN dbo.registro_visual_transectas rt ON ot.ot_id = rt.ot_id
LEFT JOIN dbo.registro_visual_abundancia ab ON rt.transecta_id = ab.transecta_id;
GO

-- =============================================
-- VISTA: Dashboard Principal - KPIs
-- =============================================

CREATE OR ALTER VIEW vw_dashboard_kpis AS
SELECT 
    COUNT(DISTINCT ot.ot_id) AS total_informes,
    COUNT(DISTINCT ot.centro_id) AS total_centros,
    COUNT(DISTINCT CASE WHEN ot.condicion_centro = 'ANAEROBICO' THEN ot.centro_id END) AS centros_anaerobicos,
    COUNT(DISTINCT CASE WHEN ot.condicion_centro = 'AEROBICO' THEN ot.centro_id END) AS centros_aerobicos,
    COUNT(DISTINCT CASE WHEN ot.requiere_revision = 1 THEN ot.ot_id END) AS informes_requieren_revision,
    SUM(ot.numero_incumplimientos) AS total_incumplimientos,
    COUNT(DISTINCT CASE WHEN ot.tipo_informe = 'SEDIMENTO' THEN ot.ot_id END) AS informes_sedimento,
    COUNT(DISTINCT CASE WHEN ot.tipo_informe = 'OXIGENO' THEN ot.ot_id END) AS informes_oxigeno,
    COUNT(DISTINCT CASE WHEN ot.tipo_informe = 'VISUAL' THEN ot.ot_id END) AS informes_visual,
    COUNT(DISTINCT CASE WHEN ot.tipo_informe = 'MIXTO' THEN ot.ot_id END) AS informes_mixtos,
    AVG(CASE WHEN mot.mot_porcentaje IS NOT NULL THEN mot.mot_porcentaje END) AS promedio_mot_general,
    AVG(CASE WHEN om.es_z_menos_1 = 1 THEN om.oxigeno_mg_l END) AS promedio_oxigeno_z1
FROM dbo.ordenes_trabajo ot
LEFT JOIN dbo.sedimento_estaciones se ON ot.ot_id = se.ot_id
LEFT JOIN dbo.sedimento_materia_organica mot ON se.estacion_id = mot.estacion_id
LEFT JOIN dbo.oxigeno_perfiles op ON ot.ot_id = op.ot_id
LEFT JOIN dbo.oxigeno_mediciones om ON op.perfil_id = om.perfil_id;
GO

-- =============================================
-- VISTA: Calidad de Extracción
-- =============================================

CREATE OR ALTER VIEW vw_calidad_extraccion AS
SELECT 
    ot.codigo_ot,
    ot.tipo_informe,
    ot.fecha_procesamiento,
    ae.tabla_afectada,
    ae.registros_esperados,
    ae.registros_extraidos,
    ae.porcentaje_completitud,
    ae.valores_fuera_rango,
    ae.tiempo_procesamiento_seg,
    ae.requiere_revision,
    CASE 
        WHEN ae.porcentaje_completitud >= 95 THEN 'EXCELENTE'
        WHEN ae.porcentaje_completitud >= 80 THEN 'BUENO'
        WHEN ae.porcentaje_completitud >= 60 THEN 'REGULAR'
        ELSE 'MALO'
    END AS calificacion_extraccion
FROM dbo.ordenes_trabajo ot
INNER JOIN dbo.auditoria_extraccion ae ON ot.ot_id = ae.ot_id;
GO

PRINT 'Vistas creadas exitosamente';
PRINT 'Total de vistas: 7';
PRINT '- vw_resumen_ordenes';
PRINT '- vw_analisis_sedimento';
PRINT '- vw_analisis_oxigeno';
PRINT '- vw_oxigeno_z1_critico';
PRINT '- vw_biodiversidad';
PRINT '- vw_dashboard_kpis';
PRINT '- vw_calidad_extraccion';
GO
