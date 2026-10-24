# SmartCity DataHub

Proyecto integrador COIL · Bases de Datos / Modelado de Datos · UTS (Bucaramanga, Colombia) · ODS 11
Autor: Jonathan Alexis Guevara Basto · Docente: Ricardo Andrés Medina Puentes

Aplicación web que implementa el Modelo Entidad-Relación (9 entidades, 3FN) para gestionar
reportes ciudadanos de incidencias urbanas, sensores IoT y cuadrillas de mantenimiento.

## Tecnologías
Python 3 · Flask · SQLite · Jinja2 · Leaflet (mapas OpenStreetMap)

## Requisitos previos
- [Python 3.9 o superior](https://www.python.org/downloads/) (marcar "Add Python to PATH" al instalar)
- [Git](https://git-scm.com/downloads)
- Conexión a internet (para instalar Flask y cargar los mapas)

## Instalación

### 1. Clonar el repositorio
```powershell
git clone https://github.com/ryoka0123/smartcity-datahub.git
cd smartcity-datahub
```

### 2. Crear y activar el entorno virtual
Windows (PowerShell):
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```
Si PowerShell bloquea el script, ejecuta una vez:
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

Linux / macOS:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Instalar dependencias
```powershell
pip install -r requirements.txt
```

### 4. Ejecutar la aplicación
```powershell
python app.py
```
Abrir en el navegador: http://127.0.0.1:5000

La base de datos `smartcity.db` se crea sola, con datos de ejemplo de Bucaramanga, la primera vez
que se ejecuta. Para reiniciarla, detén la app y borra el archivo `smartcity.db`.

### 5. (Opcional) Prueba rápida
```powershell
python tests_smoke.py
```
Imprime el código de respuesta de cada ruta. Nota: esta prueba agrega datos a la base, así que
borra `smartcity.db` después si quieres volver a los datos originales.

## Estructura
- `schema.sql`: tablas con PK, FK y restricciones (el MER).
- `seed.sql`: datos de ejemplo de Bucaramanga.
- `app.py`: rutas y lógica de negocio.
- `templates/` y `static/`: interfaz.
- `tests_smoke.py`: prueba rápida de las rutas.

## Funcionalidades
- Panel con KPIs, mapa de incidencias y reportes por categoría.
- Registro de reportes con ubicación en mapa (reutiliza ciudadanos existentes por documento).
- Asignación de cuadrilla (tabla asociativa `intervencion_mantenimiento`) y cierre con costo.
- Sensores IoT con simulación de lecturas y alertas por umbral.
- Listado de cuadrillas con intervenciones y costos.

## Problemas comunes
- `python` no se reconoce: reinstala Python marcando "Add Python to PATH" o usa `py` en lugar de `python`.
- `No module named flask`: el entorno virtual no está activo; repite el paso 2 y el 3.
- Los mapas salen en blanco: revisa tu conexión a internet.

## Ideas futuras
Login por roles, subida real de fotos, API REST, migrar a PostgreSQL.
