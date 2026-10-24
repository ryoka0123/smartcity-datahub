# SmartCity DataHub

Proyecto integrador COIL · Bases de Datos / Modelado de Datos · UTS (Bucaramanga, Colombia) · ODS 11
Autor: Jonathan Alexis Guevara Basto · Docente: Ricardo Andrés Medina Puentes

Aplicación web que implementa el Modelo Entidad-Relación (9 entidades, 3FN) para gestionar
reportes ciudadanos de incidencias urbanas, sensores IoT y cuadrillas de mantenimiento.

## Tecnologías
Python 3 · Flask · SQLite · Jinja2 · Leaflet (mapas OpenStreetMap)

## Ejecución (Windows PowerShell)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```
Abrir http://127.0.0.1:5000. La base `smartcity.db` se crea sola con datos de ejemplo
(para reiniciarla, borra el archivo `smartcity.db`).

## Estructura
- `schema.sql`: tablas con PK, FK y restricciones (el MER).
- `seed.sql`: datos de ejemplo de Bucaramanga.
- `app.py`: rutas y lógica de negocio.
- `templates/` y `static/`: interfaz.

## Funcionalidades
- Panel con KPIs, mapa de incidencias y reportes por categoría.
- Registro de reportes con ubicación en mapa (reutiliza ciudadanos existentes por documento).
- Asignación de cuadrilla (tabla asociativa `intervencion_mantenimiento`) y cierre con costo.
- Sensores IoT con simulación de lecturas y alertas por umbral.
- Listado de cuadrillas con intervenciones y costos.

## Ideas futuras
Login por roles, subida real de fotos, API REST, migrar a PostgreSQL.
