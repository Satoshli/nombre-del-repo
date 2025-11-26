-- =============================================
-- Índices Adicionales para Optimización Power BI
-- =============================================

USE MonitoreoAmbiental;
GO

-- =============================================
-- ÍNDICES COLUMNSTORE (Para análisis masivos)
-- =============================================

-- Índice columnstore para análisis de mediciones MOT
CREATE NONCLUSTERED COLUMNSTORE INDEX IX_CS_sedimento_mot
ON dbo.sedimento_materia_organica (
    estacion_id, mot_porcentaje, promedio_estacion, 
    cumple_limite_infa, cumple_limite_post
);
GO

-- Índice columnstore para análisis de oxígeno
CREATE NONCLUSTERED COLUMNSTORE INDEX IX_CS_oxigeno_med
ON dbo.oxigeno_mediciones (
    perfil_id, profundidad_m, oxigeno_mg_l, 
    temperatura_c, saturacion_pct, es_z_menos_1, cumple_limite
);
GO

-- =============================================
-- ÍNDICES COMPUESTOS PARA QUERIES FRECUENTES
-- =============================================

-- Para análisis temporal de órdenes de trabajo
CREATE INDEX IX_ordenes_fecha_tipo ON dbo.ordenes_trabajo(fecha_muestreo, tipo_informe)
INCLUDE (centro_id, condicion_centro, numero_incumplimientos);
GO

-- Para filtros de cumplimiento en sedimento
CREATE INDEX IX_mot_cumplimiento_composite ON dbo.sedimento_materia_organica(
    cumple_limite_infa, cumple_limite_post, mot_porcentaje
) INCLUDE (estacion_id, codigo_muestra);
GO

-- Para análisis de pH/Redox conjunto
CREATE INDEX IX_phredox_cumplimiento_composite ON dbo.sedimento_ph_redox(
    cumple_conjunto, cumple_ph, cumple_redox
) INCLUDE (estacion_id, ph, potencial_redox_mv);
GO

-- Para análisis de oxígeno crítico (Z-1)
CREATE INDEX IX_oxigeno_z1_cumple ON dbo.oxigeno_mediciones(
    es_z_menos_1, cumple_limite
) INCLUDE (perfil_id, oxigeno_mg_l, profundidad_m)
WHERE es_z_menos_1 = 1;
GO

-- Para búsqueda de especies
CREATE INDEX IX_abundancia_especies ON dbo.registro_visual_abundancia(
    especie, abundancia
) INCLUDE (transecta_id, grupo_taxonomico);
GO

-- =============================================
-- ÍNDICES PARA JOINS FRECUENTES
-- =============================================

-- Optimizar JOIN entre estaciones y MOT
CREATE INDEX IX_sedimento_estaciones_ot_codigo ON dbo.sedimento_estaciones(
    ot_id, codigo_estacion
) INCLUDE (utm_este, utm_norte, profundidad_m);
GO

-- Optimizar JOIN entre perfiles y mediciones
CREATE INDEX IX_oxigeno_perfiles_ot_codigo ON dbo.oxigeno_perfiles(
    ot_id, codigo_perfil
) INCLUDE (profundidad_maxima_m);
GO

-- =============================================
-- ESTADÍSTICAS PARA OPTIMIZADOR
-- =============================================

-- Actualizar estadísticas en tablas principales
UPDATE STATISTICS dbo.ordenes_trabajo WITH FULLSCAN;
UPDATE STATISTICS dbo.centros WITH FULLSCAN;
UPDATE STATISTICS dbo.sedimento_materia_organica WITH FULLSCAN;
UPDATE STATISTICS dbo.oxigeno_mediciones WITH FULLSCAN;
GO

PRINT 'Índices adicionales creados exitosamente';
PRINT 'Se han creado:';
PRINT '- 2 índices columnstore para análisis masivo';
PRINT '- 6 índices compuestos para queries frecuentes';
PRINT '- 3 índices para optimización de JOINs';
GO
