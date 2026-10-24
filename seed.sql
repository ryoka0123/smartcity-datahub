-- Datos de ejemplo: Bucaramanga, Santander
INSERT INTO ciudad (nombre_ciudad, pais, departamento_estado, poblacion_estimada)
VALUES ('Bucaramanga', 'Colombia', 'Santander', 623000);

INSERT INTO zona_urbana (id_ciudad, nombre_zona, codigo_postal, nivel_prioridad_vial, lat_centro, lng_centro) VALUES
(1, 'Cabecera del Llano', '680003', 'Alta',  7.1186, -73.1108),
(1, 'Ciudadela Real de Minas (UTS)', '680005', 'Alta', 7.1042, -73.1235),
(1, 'Centro', '680006', 'Alta', 7.1193, -73.1227),
(1, 'San Alonso', '680004', 'Media', 7.1305, -73.1162);

INSERT INTO ciudadano (documento_identidad, nombre_completo, correo_electronico, telefono_contacto) VALUES
('1098000001', 'Jonathan Alexis Guevara Basto', 'jonathan@correo.uts.edu.co', '3000000000'),
('1098000002', 'María Fernanda Rojas', 'maria.rojas@correo.com', '3101112233'),
('1098000003', 'Carlos Andrés Pinzón', 'carlos.pinzon@correo.com', '3159998877');

INSERT INTO categoria_incidencia (nombre_categoria, tipo_ods_meta, sla_horas_respuesta, nivel_criticidad) VALUES
('Daño vial / hueco', 'ODS 11.2', 48, 'Media'),
('Falla semafórica', 'ODS 11.2', 6, 'Alta'),
('Alerta calidad del aire', 'ODS 11.6', 12, 'Alta'),
('Luminaria dañada', 'ODS 11.7', 24, 'Baja');

INSERT INTO cuadrilla_operativa (nombre_cuadrilla, especialidad_tecnica, responsable_turno, telefono_emergencia, disponible) VALUES
('Cuadrilla Vial #1', 'Pavimentación', 'Ing. Luis Prada', '3201230001', 1),
('Cuadrilla Eléctrica #2', 'Semaforización', 'Téc. Ana Ortiz', '3201230002', 0),
('Cuadrilla Alumbrado #3', 'Alumbrado público', 'Téc. Jorge Mantilla', '3201230003', 1);

INSERT INTO reporte_incidencia (id_ciudadano, id_zona, id_categoria, descripcion_problema, latitud, longitud, estado_actual) VALUES
(2, 2, 2, 'Semáforo intermitente en el cruce peatonal frente a la UTS.', 7.1042, -73.1235, 'En Atención'),
(3, 1, 1, 'Hueco profundo en el carril derecho de la carrera 33.', 7.1186, -73.1108, 'Pendiente'),
(2, 3, 4, 'Sector sin iluminación en la calle 36.', 7.1193, -73.1227, 'Resuelto'),
(1, 4, 1, 'Hundimiento de calzada cerca del puente peatonal.', 7.1305, -73.1162, 'Pendiente');

INSERT INTO intervencion_mantenimiento (id_reporte, id_cuadrilla, diagnostico_tecnico, costo_operativo, resultado_intervencion) VALUES
(1, 2, 'Falla en controlador del semáforo.', 180000, 'En Proceso');
INSERT INTO intervencion_mantenimiento (id_reporte, id_cuadrilla, fecha_cierre, diagnostico_tecnico, costo_operativo, resultado_intervencion) VALUES
(3, 3, datetime('now','localtime'), 'Cambio de balasto y bombilla LED.', 95000, 'Resuelto');

INSERT INTO sensor_iot (id_zona, codigo_serie, tipo_sensor, latitud, longitud, estado_operativo, fecha_instalacion) VALUES
(2, 'SEN-BGA-01', 'Calidad del aire PM2.5', 7.1050, -73.1230, 'Activo', '2026-03-10'),
(3, 'SEN-BGA-02', 'Flujo vehicular', 7.1190, -73.1230, 'Activo', '2026-03-12'),
(1, 'SEN-BGA-03', 'Ruido ambiental', 7.1180, -73.1110, 'Activo', '2026-04-02');

INSERT INTO lectura_sensor (id_sensor, valor_medido, unidad_medida, alerta_umbral_critico) VALUES
(1, 18.4, 'µg/m³', 0),
(2, 82, 'veh/min', 1),
(3, 64.2, 'dB', 0);
