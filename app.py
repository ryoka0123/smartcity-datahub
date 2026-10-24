"""SmartCity DataHub - Proyecto COIL (UTS, Colombia)
Aplicación web en Flask + SQLite que implementa el MER de 9 entidades
para gestionar incidencias urbanas, sensores IoT y cuadrillas (ODS 11).
Autor: Jonathan Alexis Guevara Basto
"""
import os
import random
import sqlite3

from flask import Flask, g, render_template, request, redirect, url_for, flash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "smartcity.db")

app = Flask(__name__)
app.secret_key = "smartcity-uts-dev"  # solo para desarrollo

ESTADOS = ["Pendiente", "En Atención", "Resuelto"]

# Umbral de alerta y rango de simulación por tipo de sensor
SENSOR_CFG = {
    "Calidad del aire PM2.5": {"unidad": "µg/m³", "umbral": 35, "rango": (8, 60)},
    "Flujo vehicular": {"unidad": "veh/min", "umbral": 75, "rango": (20, 100)},
    "Ruido ambiental": {"unidad": "dB", "umbral": 70, "rango": (45, 85)},
}


# ---------- Base de datos ----------
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Crea las tablas y carga datos de ejemplo si la BD no existe."""
    if os.path.exists(DB_PATH):
        return
    con = sqlite3.connect(DB_PATH)
    for archivo in ("schema.sql", "seed.sql"):
        with open(os.path.join(BASE_DIR, archivo), encoding="utf-8") as f:
            con.executescript(f.read())
    con.commit()
    con.close()


def query(sql, args=(), one=False):
    cur = get_db().execute(sql, args)
    rows = cur.fetchall()
    return (rows[0] if rows else None) if one else rows


REPORTE_SELECT = """
    SELECT r.*, z.nombre_zona, c.nombre_categoria, c.sla_horas_respuesta,
           c.nivel_criticidad, u.nombre_completo
    FROM reporte_incidencia r
    JOIN zona_urbana z ON z.id_zona = r.id_zona
    JOIN categoria_incidencia c ON c.id_categoria = r.id_categoria
    JOIN ciudadano u ON u.id_ciudadano = r.id_ciudadano
"""


# ---------- Rutas ----------
@app.route("/")
def dashboard():
    kpis = {
        "total": query("SELECT COUNT(*) n FROM reporte_incidencia", one=True)["n"],
        "pendientes": query("SELECT COUNT(*) n FROM reporte_incidencia WHERE estado_actual='Pendiente'", one=True)["n"],
        "atencion": query("SELECT COUNT(*) n FROM reporte_incidencia WHERE estado_actual='En Atención'", one=True)["n"],
        "resueltos": query("SELECT COUNT(*) n FROM reporte_incidencia WHERE estado_actual='Resuelto'", one=True)["n"],
        "alertas": query("SELECT COUNT(*) n FROM lectura_sensor WHERE alerta_umbral_critico=1", one=True)["n"],
    }
    por_categoria = query("""
        SELECT c.nombre_categoria, COUNT(r.id_reporte) n
        FROM categoria_incidencia c
        LEFT JOIN reporte_incidencia r ON r.id_categoria = c.id_categoria
        GROUP BY c.id_categoria""")
    reportes = query(REPORTE_SELECT + " ORDER BY r.fecha_hora_reporte DESC, r.id_reporte DESC")
    return render_template("dashboard.html", kpis=kpis, por_categoria=por_categoria,
                           reportes=reportes)


@app.route("/reportes")
def reportes():
    estado = request.args.get("estado", "")
    if estado in ESTADOS:
        rows = query(REPORTE_SELECT + " WHERE r.estado_actual=? ORDER BY r.id_reporte DESC", (estado,))
    else:
        rows = query(REPORTE_SELECT + " ORDER BY r.id_reporte DESC")
    return render_template("reportes.html", reportes=rows, estado=estado, estados=ESTADOS)


@app.route("/reportes/nuevo", methods=["GET", "POST"])
def nuevo_reporte():
    zonas = query("SELECT * FROM zona_urbana ORDER BY nombre_zona")
    categorias = query("SELECT * FROM categoria_incidencia ORDER BY nombre_categoria")
    if request.method == "POST":
        f = request.form
        doc = f["documento"].strip()
        nombre = f["nombre"].strip()
        correo = f["correo"].strip()
        desc = f["descripcion"].strip()
        if not (doc and nombre and correo and desc and f.get("latitud") and f.get("longitud")):
            flash("Completa todos los campos y marca la ubicación en el mapa.", "error")
            return render_template("nuevo_reporte.html", zonas=zonas, categorias=categorias, form=f)
        db = get_db()
        # Si el ciudadano ya existe se reutiliza (evita duplicados, UNIQUE documento)
        u = query("SELECT id_ciudadano FROM ciudadano WHERE documento_identidad=?", (doc,), one=True)
        if u:
            id_ciudadano = u["id_ciudadano"]
        else:
            cur = db.execute(
                "INSERT INTO ciudadano (documento_identidad, nombre_completo, correo_electronico, telefono_contacto) VALUES (?,?,?,?)",
                (doc, nombre, correo, f.get("telefono", "").strip()))
            id_ciudadano = cur.lastrowid
        cur = db.execute(
            """INSERT INTO reporte_incidencia
               (id_ciudadano, id_zona, id_categoria, descripcion_problema, latitud, longitud, url_evidencia_foto)
               VALUES (?,?,?,?,?,?,?)""",
            (id_ciudadano, f["id_zona"], f["id_categoria"], desc,
             float(f["latitud"]), float(f["longitud"]), f.get("foto", "").strip() or None))
        db.commit()
        flash(f"Reporte #{cur.lastrowid} registrado correctamente.", "ok")
        return redirect(url_for("detalle_reporte", id_reporte=cur.lastrowid))
    return render_template("nuevo_reporte.html", zonas=zonas, categorias=categorias, form={})


@app.route("/reportes/<int:id_reporte>")
def detalle_reporte(id_reporte):
    r = query(REPORTE_SELECT + " WHERE r.id_reporte=?", (id_reporte,), one=True)
    if r is None:
        return render_template("404.html"), 404
    intervenciones = query("""
        SELECT i.*, q.nombre_cuadrilla, q.especialidad_tecnica
        FROM intervencion_mantenimiento i
        JOIN cuadrilla_operativa q ON q.id_cuadrilla = i.id_cuadrilla
        WHERE i.id_reporte=? ORDER BY i.id_intervencion DESC""", (id_reporte,))
    cuadrillas = query("SELECT * FROM cuadrilla_operativa WHERE disponible=1")
    return render_template("detalle.html", r=r, intervenciones=intervenciones, cuadrillas=cuadrillas)


@app.route("/reportes/<int:id_reporte>/asignar", methods=["POST"])
def asignar(id_reporte):
    db = get_db()
    id_cuadrilla = request.form["id_cuadrilla"]
    db.execute(
        "INSERT INTO intervencion_mantenimiento (id_reporte, id_cuadrilla, diagnostico_tecnico) VALUES (?,?,?)",
        (id_reporte, id_cuadrilla, request.form.get("diagnostico", "").strip()))
    db.execute("UPDATE reporte_incidencia SET estado_actual='En Atención' WHERE id_reporte=?", (id_reporte,))
    db.execute("UPDATE cuadrilla_operativa SET disponible=0 WHERE id_cuadrilla=?", (id_cuadrilla,))
    db.commit()
    flash("Cuadrilla asignada. El reporte pasó a 'En Atención'.", "ok")
    return redirect(url_for("detalle_reporte", id_reporte=id_reporte))


@app.route("/intervenciones/<int:id_intervencion>/cerrar", methods=["POST"])
def cerrar(id_intervencion):
    db = get_db()
    i = query("SELECT * FROM intervencion_mantenimiento WHERE id_intervencion=?", (id_intervencion,), one=True)
    if i is None:
        return render_template("404.html"), 404
    try:
        costo = float(request.form.get("costo") or 0)
    except ValueError:
        costo = 0
    db.execute(
        """UPDATE intervencion_mantenimiento
           SET fecha_cierre=datetime('now','localtime'), costo_operativo=?, resultado_intervencion='Resuelto'
           WHERE id_intervencion=?""", (costo, id_intervencion))
    db.execute("UPDATE reporte_incidencia SET estado_actual='Resuelto' WHERE id_reporte=?", (i["id_reporte"],))
    db.execute("UPDATE cuadrilla_operativa SET disponible=1 WHERE id_cuadrilla=?", (i["id_cuadrilla"],))
    db.commit()
    flash("Intervención cerrada y reporte marcado como Resuelto.", "ok")
    return redirect(url_for("detalle_reporte", id_reporte=i["id_reporte"]))


@app.route("/sensores")
def sensores():
    rows = query("""
        SELECT s.*, z.nombre_zona,
          (SELECT valor_medido FROM lectura_sensor l WHERE l.id_sensor=s.id_sensor ORDER BY l.id_lectura DESC LIMIT 1) AS ultimo_valor,
          (SELECT unidad_medida FROM lectura_sensor l WHERE l.id_sensor=s.id_sensor ORDER BY l.id_lectura DESC LIMIT 1) AS unidad,
          (SELECT alerta_umbral_critico FROM lectura_sensor l WHERE l.id_sensor=s.id_sensor ORDER BY l.id_lectura DESC LIMIT 1) AS alerta,
          (SELECT fecha_hora_lectura FROM lectura_sensor l WHERE l.id_sensor=s.id_sensor ORDER BY l.id_lectura DESC LIMIT 1) AS fecha
        FROM sensor_iot s JOIN zona_urbana z ON z.id_zona = s.id_zona""")
    historial = query("""
        SELECT l.*, s.codigo_serie, s.tipo_sensor FROM lectura_sensor l
        JOIN sensor_iot s ON s.id_sensor = l.id_sensor
        ORDER BY l.id_lectura DESC LIMIT 15""")
    return render_template("sensores.html", sensores=rows, historial=historial)


@app.route("/sensores/<int:id_sensor>/simular", methods=["POST"])
def simular_lectura(id_sensor):
    """Simula una lectura IoT (en un sistema real llegaría por HTTP/MQTT)."""
    s = query("SELECT * FROM sensor_iot WHERE id_sensor=?", (id_sensor,), one=True)
    if s is None:
        return render_template("404.html"), 404
    cfg = SENSOR_CFG.get(s["tipo_sensor"], {"unidad": "u", "umbral": 100, "rango": (0, 120)})
    valor = round(random.uniform(*cfg["rango"]), 1)
    alerta = 1 if valor > cfg["umbral"] else 0
    db = get_db()
    db.execute(
        "INSERT INTO lectura_sensor (id_sensor, valor_medido, unidad_medida, alerta_umbral_critico) VALUES (?,?,?,?)",
        (id_sensor, valor, cfg["unidad"], alerta))
    db.commit()
    flash(f"Lectura registrada: {valor} {cfg['unidad']}" + (" ⚠ ALERTA" if alerta else ""),
          "error" if alerta else "ok")
    return redirect(url_for("sensores"))


@app.route("/cuadrillas")
def cuadrillas():
    rows = query("""
        SELECT q.*, COUNT(i.id_intervencion) AS total,
               COALESCE(SUM(i.costo_operativo),0) AS costo
        FROM cuadrilla_operativa q
        LEFT JOIN intervencion_mantenimiento i ON i.id_cuadrilla = q.id_cuadrilla
        GROUP BY q.id_cuadrilla""")
    return render_template("cuadrillas.html", cuadrillas=rows)


@app.errorhandler(404)
def no_encontrado(_e):
    return render_template("404.html"), 404


init_db()

if __name__ == "__main__":
    app.run(debug=True)
