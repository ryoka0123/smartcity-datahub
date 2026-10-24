-- SmartCity DataHub - esquema relacional (3FN) basado en el MER del proyecto COIL
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS ciudad (
    id_ciudad INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_ciudad TEXT NOT NULL,
    pais TEXT NOT NULL DEFAULT 'Colombia',
    departamento_estado TEXT NOT NULL,
    poblacion_estimada INTEGER
);

CREATE TABLE IF NOT EXISTS zona_urbana (
    id_zona INTEGER PRIMARY KEY AUTOINCREMENT,
    id_ciudad INTEGER NOT NULL REFERENCES ciudad(id_ciudad),
    nombre_zona TEXT NOT NULL,
    codigo_postal TEXT,
    nivel_prioridad_vial TEXT DEFAULT 'Media',
    lat_centro REAL,
    lng_centro REAL
);

CREATE TABLE IF NOT EXISTS ciudadano (
    id_ciudadano INTEGER PRIMARY KEY AUTOINCREMENT,
    documento_identidad TEXT NOT NULL UNIQUE,
    nombre_completo TEXT NOT NULL,
    correo_electronico TEXT NOT NULL,
    telefono_contacto TEXT,
    rol TEXT NOT NULL DEFAULT 'Ciudadano',
    clave_acceso TEXT NOT NULL DEFAULT '123456',
    fecha_registro TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS categoria_incidencia (
    id_categoria INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_categoria TEXT NOT NULL,
    tipo_ods_meta TEXT DEFAULT 'ODS 11',
    sla_horas_respuesta INTEGER NOT NULL,
    nivel_criticidad TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reporte_incidencia (
    id_reporte INTEGER PRIMARY KEY AUTOINCREMENT,
    id_ciudadano INTEGER NOT NULL REFERENCES ciudadano(id_ciudadano),
    id_zona INTEGER NOT NULL REFERENCES zona_urbana(id_zona),
    id_categoria INTEGER NOT NULL REFERENCES categoria_incidencia(id_categoria),
    fecha_hora_reporte TEXT DEFAULT (datetime('now','localtime')),
    descripcion_problema TEXT NOT NULL,
    latitud REAL NOT NULL,
    longitud REAL NOT NULL,
    url_evidencia_foto TEXT,
    estado_actual TEXT NOT NULL DEFAULT 'Pendiente'
        CHECK (estado_actual IN ('Pendiente','En Atención','Resuelto'))
);

CREATE TABLE IF NOT EXISTS sensor_iot (
    id_sensor INTEGER PRIMARY KEY AUTOINCREMENT,
    id_zona INTEGER NOT NULL REFERENCES zona_urbana(id_zona),
    codigo_serie TEXT NOT NULL UNIQUE,
    tipo_sensor TEXT NOT NULL,
    latitud REAL NOT NULL,
    longitud REAL NOT NULL,
    estado_operativo TEXT DEFAULT 'Activo',
    fecha_instalacion TEXT
);

CREATE TABLE IF NOT EXISTS lectura_sensor (
    id_lectura INTEGER PRIMARY KEY AUTOINCREMENT,
    id_sensor INTEGER NOT NULL REFERENCES sensor_iot(id_sensor),
    fecha_hora_lectura TEXT DEFAULT (datetime('now','localtime')),
    valor_medido REAL NOT NULL,
    unidad_medida TEXT NOT NULL,
    alerta_umbral_critico INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS cuadrilla_operativa (
    id_cuadrilla INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_cuadrilla TEXT NOT NULL,
    especialidad_tecnica TEXT NOT NULL,
    responsable_turno TEXT NOT NULL,
    telefono_emergencia TEXT,
    disponible INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS intervencion_mantenimiento (
    id_intervencion INTEGER PRIMARY KEY AUTOINCREMENT,
    id_reporte INTEGER NOT NULL REFERENCES reporte_incidencia(id_reporte),
    id_cuadrilla INTEGER NOT NULL REFERENCES cuadrilla_operativa(id_cuadrilla),
    fecha_asignacion TEXT DEFAULT (datetime('now','localtime')),
    fecha_cierre TEXT,
    diagnostico_tecnico TEXT,
    costo_operativo REAL DEFAULT 0,
    resultado_intervencion TEXT DEFAULT 'En Proceso'
);
