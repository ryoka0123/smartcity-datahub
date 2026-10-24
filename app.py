"""SmartCity DataHub - Proyecto COIL (UTS, Colombia)
Aplicación web en Flask + SQLite que implementa el MER de 9 entidades
para gestionar incidencias urbanas, sensores IoT y cuadrillas (ODS 11).
Autor: Jonathan Alexis Guevara Basto
"""
from functools import wraps
import json
import os
import random
import sqlite3
import urllib.error
import urllib.request

from flask import Flask, g, render_template, request, redirect, url_for, flash, session

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "smartcity.db")

app = Flask(__name__)
app.secret_key = "smartcity-uts-dev"  # solo para desarrollo

ESTADOS = ["Pendiente", "En Atención", "Resuelto"]

# Configuración de sensores conectados a la API real de Open-Meteo (Bucaramanga)
SENSOR_CFG = {
    "Calidad del aire PM2.5": {
        "campo_api": "pm2_5",
        "unidad": "µg/m³",
        "umbral": 35.0,
        "rango": (8, 50),
    },
    "Emisión vehicular CO (Tráfico)": {
        "campo_api": "carbon_monoxide",
        "unidad": "µg/m³",
        "umbral": 400.0,
        "rango": (150, 500),
    },
    "Material particulado PM10": {
        "campo_api": "pm10",
        "unidad": "µg/m³",
        "umbral": 50.0,
        "rango": (15, 70),
    },
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
    """Crea las tablas y carga datos de ejemplo si la BD no existe,
    y asegura que los sensores y columnas de login estén actualizados."""
    con = sqlite3.connect(DB_PATH)
    existe = con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='sensor_iot'"
    ).fetchone()
    if not existe:
        for archivo in ("schema.sql", "seed.sql"):
            with open(os.path.join(BASE_DIR, archivo), encoding="utf-8") as f:
                con.executescript(f.read())
    else:
        con.execute(
            "UPDATE sensor_iot SET tipo_sensor='Emisión vehicular CO (Tráfico)' WHERE codigo_serie='SEN-BGA-02'"
        )
        con.execute(
            "UPDATE sensor_iot SET tipo_sensor='Material particulado PM10' WHERE codigo_serie='SEN-BGA-03'"
        )
        cols_ciud = [c[1] for c in con.execute("PRAGMA table_info(ciudadano)").fetchall()]
        if "rol" not in cols_ciud:
            con.execute("ALTER TABLE ciudadano ADD COLUMN rol TEXT NOT NULL DEFAULT 'Ciudadano'")
        if "clave_acceso" not in cols_ciud:
            con.execute("ALTER TABLE ciudadano ADD COLUMN clave_acceso TEXT NOT NULL DEFAULT '123456'")
        con.execute(
            "UPDATE ciudadano SET rol='Administrador', clave_acceso='uts2026' WHERE documento_identidad='1098000001'"
        )
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


# ---------- Control de Acceso y Separación de Roles ----------
def es_admin():
    u = session.get("usuario")
    return bool(u and u.get("rol") == "Administrador")


def solo_admin(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("usuario"):
            flash("Inicia sesión para continuar.", "error")
            return redirect(url_for("login"))
        if not es_admin():
            flash("Acceso restringido: esta sección es exclusiva del rol Administrador.", "error")
            return redirect(url_for("dashboard"))
        return fn(*args, **kwargs)
    return wrapper


@app.before_request
def verificar_sesion():
    rutas_publicas = {"login", "registro", "static"}
    if request.endpoint and request.endpoint not in rutas_publicas:
        if not session.get("usuario"):
            return redirect(url_for("login"))


# ---------- Rutas ----------
@app.route("/")
def dashboard():
    u = session["usuario"]
    if es_admin():
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
    else:
        id_c = u["id_ciudadano"]
        kpis = {
            "total": query("SELECT COUNT(*) n FROM reporte_incidencia WHERE id_ciudadano=?", (id_c,), one=True)["n"],
            "pendientes": query("SELECT COUNT(*) n FROM reporte_incidencia WHERE id_ciudadano=? AND estado_actual='Pendiente'", (id_c,), one=True)["n"],
            "atencion": query("SELECT COUNT(*) n FROM reporte_incidencia WHERE id_ciudadano=? AND estado_actual='En Atención'", (id_c,), one=True)["n"],
            "resueltos": query("SELECT COUNT(*) n FROM reporte_incidencia WHERE id_ciudadano=? AND estado_actual='Resuelto'", (id_c,), one=True)["n"],
            "alertas": query("SELECT COUNT(*) n FROM lectura_sensor WHERE alerta_umbral_critico=1", one=True)["n"],
        }
        por_categoria = query("""
            SELECT c.nombre_categoria, COUNT(r.id_reporte) n
            FROM categoria_incidencia c
            LEFT JOIN reporte_incidencia r ON r.id_categoria = c.id_categoria AND r.id_ciudadano = ?
            GROUP BY c.id_categoria""", (id_c,))
        reportes = query(
            REPORTE_SELECT + " WHERE r.id_ciudadano=? ORDER BY r.fecha_hora_reporte DESC, r.id_reporte DESC",
            (id_c,),
        )
    return render_template("dashboard.html", kpis=kpis, por_categoria=por_categoria,
                           reportes=reportes)


@app.route("/reportes")
def reportes():
    estado = request.args.get("estado", "")
    u = session["usuario"]
    if es_admin():
        if estado in ESTADOS:
            rows = query(REPORTE_SELECT + " WHERE r.estado_actual=? ORDER BY r.id_reporte DESC", (estado,))
        else:
            rows = query(REPORTE_SELECT + " ORDER BY r.id_reporte DESC")
    else:
        if estado in ESTADOS:
            rows = query(
                REPORTE_SELECT + " WHERE r.id_ciudadano=? AND r.estado_actual=? ORDER BY r.id_reporte DESC",
                (u["id_ciudadano"], estado),
            )
        else:
            rows = query(
                REPORTE_SELECT + " WHERE r.id_ciudadano=? ORDER BY r.id_reporte DESC",
                (u["id_ciudadano"],),
            )
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
    form_inicial = {}
    if session.get("usuario"):
        u = session["usuario"]
        form_inicial = {
            "documento": u.get("documento", ""),
            "nombre": u.get("nombre", ""),
            "correo": u.get("correo", ""),
            "telefono": u.get("telefono", ""),
        }
    return render_template("nuevo_reporte.html", zonas=zonas, categorias=categorias, form=form_inicial)


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
@solo_admin
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
@solo_admin
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


def consultar_open_meteo_real(lat, lng, campo_api):
    """Consulta en tiempo real la API satelital/estaciones de Open-Meteo Air Quality
    para las coordenadas exactas del sensor en Bucaramanga (gratis, sin API key)."""
    url = (
        "https://air-quality-api.open-meteo.com/v1/air-quality"
        f"?latitude={lat}&longitude={lng}&current=pm2_5,pm10,carbon_monoxide,nitrogen_dioxide"
    )
    try:
        with urllib.request.urlopen(url, timeout=6) as resp:
            datos = json.load(resp)
            return datos.get("current", {}).get(campo_api)
    except (urllib.error.URLError, TimeoutError, KeyError, ValueError):
        return None


def registrar_lectura_sensor(s):
    """Consulta el valor real en Open-Meteo para el sensor `s` y lo guarda en BD."""
    cfg = SENSOR_CFG.get(
        s["tipo_sensor"],
        {"campo_api": "pm2_5", "unidad": "µg/m³", "umbral": 50.0, "rango": (10, 60)},
    )
    valor = consultar_open_meteo_real(s["latitud"], s["longitud"], cfg["campo_api"])
    if valor is not None:
        origen = "API Real Open-Meteo"
    else:
        valor = random.uniform(*cfg["rango"])
        origen = "Respaldo local (sin conexión)"
    valor = round(float(valor), 1)
    alerta = 1 if valor > cfg["umbral"] else 0
    db = get_db()
    db.execute(
        "INSERT INTO lectura_sensor (id_sensor, valor_medido, unidad_medida, alerta_umbral_critico) VALUES (?,?,?,?)",
        (s["id_sensor"], valor, cfg["unidad"], alerta),
    )
    db.commit()
    return valor, cfg["unidad"], alerta, origen


@app.route("/sensores/<int:id_sensor>/simular", methods=["POST"])
def simular_lectura(id_sensor):
    """Consulta la lectura en tiempo real desde Open-Meteo para el sensor seleccionado."""
    s = query("SELECT * FROM sensor_iot WHERE id_sensor=?", (id_sensor,), one=True)
    if s is None:
        return render_template("404.html"), 404
    valor, unidad, alerta, origen = registrar_lectura_sensor(s)
    flash(
        f"[{s['codigo_serie']}] Lectura ({origen}): {valor} {unidad}"
        + (" ⚠ ALERTA CRÍTICA" if alerta else " (Normal)"),
        "error" if alerta else "ok",
    )
    return redirect(url_for("sensores"))


@app.route("/sensores/actualizar-todos", methods=["POST"])
def actualizar_todos_sensores():
    """Consulta los 3 sensores de Bucaramanga en tiempo real contra Open-Meteo."""
    sensores_lista = query("SELECT * FROM sensor_iot")
    for s in sensores_lista:
        registrar_lectura_sensor(s)
    flash(
        "Los 3 sensores de Bucaramanga se actualizaron en tiempo real desde la API de Open-Meteo.",
        "ok",
    )
    return redirect(url_for("sensores"))


@app.route("/cuadrillas", methods=["GET", "POST"])
@solo_admin
def cuadrillas():
    if request.method == "POST":
        nombre = request.form.get("nombre_cuadrilla", "").strip()
        esp = request.form.get("especialidad_tecnica", "").strip()
        resp = request.form.get("responsable_turno", "").strip()
        tel = request.form.get("telefono_emergencia", "").strip()
        if nombre and esp and resp:
            db = get_db()
            db.execute(
                """INSERT INTO cuadrilla_operativa
                   (nombre_cuadrilla, especialidad_tecnica, responsable_turno, telefono_emergencia, disponible)
                   VALUES (?,?,?,?,1)""",
                (nombre, esp, resp, tel),
            )
            db.commit()
            flash("Cuadrilla creada correctamente (INSERT en CUADRILLA_OPERATIVA).", "ok")
        return redirect(url_for("cuadrillas"))

    rows = query("""
        SELECT q.*, COUNT(i.id_intervencion) AS total,
               COALESCE(SUM(i.costo_operativo),0) AS costo
        FROM cuadrilla_operativa q
        LEFT JOIN intervencion_mantenimiento i ON i.id_cuadrilla = q.id_cuadrilla
        GROUP BY q.id_cuadrilla
        ORDER BY q.id_cuadrilla DESC""")
    return render_template("cuadrillas.html", cuadrillas=rows, editar=None)


@app.route("/cuadrillas/<int:id_cuadrilla>/editar", methods=["GET", "POST"])
@solo_admin
def editar_cuadrilla(id_cuadrilla):
    q = query("SELECT * FROM cuadrilla_operativa WHERE id_cuadrilla=?", (id_cuadrilla,), one=True)
    if q is None:
        return render_template("404.html"), 404
    if request.method == "POST":
        db = get_db()
        db.execute(
            """UPDATE cuadrilla_operativa
               SET nombre_cuadrilla=?, especialidad_tecnica=?, responsable_turno=?,
                   telefono_emergencia=?, disponible=?
               WHERE id_cuadrilla=?""",
            (
                request.form["nombre_cuadrilla"].strip(),
                request.form["especialidad_tecnica"].strip(),
                request.form["responsable_turno"].strip(),
                request.form.get("telefono_emergencia", "").strip(),
                int(request.form.get("disponible", 1)),
                id_cuadrilla,
            ),
        )
        db.commit()
        flash(f"Cuadrilla #{id_cuadrilla} actualizada (UPDATE).", "ok")
        return redirect(url_for("cuadrillas"))
    rows = query("""
        SELECT q.*, COUNT(i.id_intervencion) AS total,
               COALESCE(SUM(i.costo_operativo),0) AS costo
        FROM cuadrilla_operativa q
        LEFT JOIN intervencion_mantenimiento i ON i.id_cuadrilla = q.id_cuadrilla
        GROUP BY q.id_cuadrilla
        ORDER BY q.id_cuadrilla DESC""")
    return render_template("cuadrillas.html", cuadrillas=rows, editar=q)


@app.route("/cuadrillas/<int:id_cuadrilla>/eliminar", methods=["POST"])
@solo_admin
def eliminar_cuadrilla(id_cuadrilla):
    tiene = query(
        "SELECT COUNT(*) n FROM intervencion_mantenimiento WHERE id_cuadrilla=?",
        (id_cuadrilla,),
        one=True,
    )["n"]
    if tiene > 0:
        flash(
            "No se puede eliminar: la cuadrilla tiene intervenciones asociadas (Integridad Referencial FK).",
            "error",
        )
        return redirect(url_for("cuadrillas"))
    db = get_db()
    db.execute("DELETE FROM cuadrilla_operativa WHERE id_cuadrilla=?", (id_cuadrilla,))
    db.commit()
    flash(f"Cuadrilla #{id_cuadrilla} eliminada (DELETE).", "ok")
    return redirect(url_for("cuadrillas"))


@app.route("/reportes/<int:id_reporte>/editar", methods=["GET", "POST"])
def editar_reporte(id_reporte):
    r = query(REPORTE_SELECT + " WHERE r.id_reporte=?", (id_reporte,), one=True)
    if r is None:
        return render_template("404.html"), 404
    u = session["usuario"]
    if not es_admin() and r["id_ciudadano"] != u["id_ciudadano"]:
        flash("Solo puedes editar tus propios reportes.", "error")
        return redirect(url_for("reportes"))
    zonas = query("SELECT * FROM zona_urbana ORDER BY nombre_zona")
    categorias = query("SELECT * FROM categoria_incidencia ORDER BY nombre_categoria")
    if request.method == "POST":
        nuevo_estado = request.form.get("estado_actual", r["estado_actual"]) if es_admin() else r["estado_actual"]
        db = get_db()
        db.execute(
            """UPDATE reporte_incidencia
               SET id_zona=?, id_categoria=?, descripcion_problema=?, estado_actual=?
               WHERE id_reporte=?""",
            (
                request.form["id_zona"],
                request.form["id_categoria"],
                request.form["descripcion"].strip(),
                nuevo_estado,
                id_reporte,
            ),
        )
        db.commit()
        flash(f"Reporte #{id_reporte} actualizado correctamente (UPDATE).", "ok")
        return redirect(url_for("detalle_reporte", id_reporte=id_reporte))
    return render_template(
        "editar_reporte.html", r=r, zonas=zonas, categorias=categorias, estados=ESTADOS
    )


@app.route("/reportes/<int:id_reporte>/eliminar", methods=["POST"])
def eliminar_reporte(id_reporte):
    r = query("SELECT * FROM reporte_incidencia WHERE id_reporte=?", (id_reporte,), one=True)
    if r is None:
        return render_template("404.html"), 404
    u = session["usuario"]
    if not es_admin() and r["id_ciudadano"] != u["id_ciudadano"]:
        flash("Solo puedes eliminar tus propios reportes.", "error")
        return redirect(url_for("reportes"))
    db = get_db()
    db.execute("DELETE FROM intervencion_mantenimiento WHERE id_reporte=?", (id_reporte,))
    db.execute("DELETE FROM reporte_incidencia WHERE id_reporte=?", (id_reporte,))
    db.commit()
    flash(f"Reporte #{id_reporte} eliminado correctamente (DELETE).", "ok")
    return redirect(url_for("reportes"))


# ---------- CRUD Independiente de Usuarios / Ciudadanos (Solo Admin) ----------
@app.route("/usuarios", methods=["GET", "POST"])
@solo_admin
def usuarios():
    if request.method == "POST":
        doc = request.form.get("documento", "").strip()
        nombre = request.form.get("nombre", "").strip()
        correo = request.form.get("correo", "").strip()
        tel = request.form.get("telefono", "").strip()
        rol = request.form.get("rol", "Ciudadano")
        clave = request.form.get("clave", "").strip() or "123456"
        if not (doc and nombre and correo):
            flash("Completa documento, nombre y correo.", "error")
            return redirect(url_for("usuarios"))
        existe = query(
            "SELECT id_ciudadano FROM ciudadano WHERE documento_identidad=?", (doc,), one=True
        )
        if existe:
            flash("Ya existe un ciudadano con ese documento de identidad (UNIQUE).", "error")
            return redirect(url_for("usuarios"))
        db = get_db()
        db.execute(
            """INSERT INTO ciudadano
               (documento_identidad, nombre_completo, correo_electronico, telefono_contacto, rol, clave_acceso)
               VALUES (?,?,?,?,?,?)""",
            (doc, nombre, correo, tel, rol, clave),
        )
        db.commit()
        flash(f"Usuario '{nombre}' creado correctamente (INSERT en CIUDADANO).", "ok")
        return redirect(url_for("usuarios"))

    lista = query("""
        SELECT u.*, COUNT(r.id_reporte) AS total_reportes
        FROM ciudadano u
        LEFT JOIN reporte_incidencia r ON r.id_ciudadano = u.id_ciudadano
        GROUP BY u.id_ciudadano
        ORDER BY u.id_ciudadano DESC""")
    return render_template("usuarios.html", usuarios=lista, editar=None)


@app.route("/usuarios/<int:id_ciudadano>/editar", methods=["GET", "POST"])
@solo_admin
def editar_usuario(id_ciudadano):
    u = query("SELECT * FROM ciudadano WHERE id_ciudadano=?", (id_ciudadano,), one=True)
    if u is None:
        return render_template("404.html"), 404
    if request.method == "POST":
        nombre = request.form["nombre"].strip()
        correo = request.form["correo"].strip()
        tel = request.form.get("telefono", "").strip()
        rol = request.form.get("rol", "Ciudadano")
        nueva_clave = request.form.get("clave", "").strip()
        db = get_db()
        if nueva_clave:
            db.execute(
                """UPDATE ciudadano
                   SET nombre_completo=?, correo_electronico=?, telefono_contacto=?, rol=?, clave_acceso=?
                   WHERE id_ciudadano=?""",
                (nombre, correo, tel, rol, nueva_clave, id_ciudadano),
            )
        else:
            db.execute(
                """UPDATE ciudadano
                   SET nombre_completo=?, correo_electronico=?, telefono_contacto=?, rol=?
                   WHERE id_ciudadano=?""",
                (nombre, correo, tel, rol, id_ciudadano),
            )
        db.commit()
        flash(f"Usuario #{id_ciudadano} actualizado correctamente (UPDATE).", "ok")
        return redirect(url_for("usuarios"))

    lista = query("""
        SELECT u.*, COUNT(r.id_reporte) AS total_reportes
        FROM ciudadano u
        LEFT JOIN reporte_incidencia r ON r.id_ciudadano = u.id_ciudadano
        GROUP BY u.id_ciudadano
        ORDER BY u.id_ciudadano DESC""")
    return render_template("usuarios.html", usuarios=lista, editar=u)


@app.route("/usuarios/<int:id_ciudadano>/eliminar", methods=["POST"])
@solo_admin
def eliminar_usuario(id_ciudadano):
    tiene = query(
        "SELECT COUNT(*) n FROM reporte_incidencia WHERE id_ciudadano=?",
        (id_ciudadano,),
        one=True,
    )["n"]
    if tiene > 0:
        flash(
            "No se puede eliminar: el ciudadano tiene reportes registrados (Integridad Referencial FK).",
            "error",
        )
        return redirect(url_for("usuarios"))
    db = get_db()
    db.execute("DELETE FROM ciudadano WHERE id_ciudadano=?", (id_ciudadano,))
    db.commit()
    flash(f"Usuario #{id_ciudadano} eliminado (DELETE).", "ok")
    return redirect(url_for("usuarios"))


TABLAS_MER = [
    ("ciudad", "Entidad fuerte: almacena las ciudades donde opera el sistema (1:N con zona_urbana)."),
    ("zona_urbana", "Comunas o sectores viales de la ciudad (1:N con reporte_incidencia y sensor_iot)."),
    ("ciudadano", "Usuarios que registran reportes de incidencias (UNIQUE documento_identidad)."),
    ("categoria_incidencia", "Clasificación por meta ODS 11, criticidad y SLA en horas."),
    ("reporte_incidencia", "Entidad central: reportes georreferenciados con estado y enlaces FK."),
    ("sensor_iot", "Dispositivos de telemetría ambiental instalados por zona urbana."),
    ("lectura_sensor", "Mediciones históricas y en tiempo real (API Open-Meteo) de cada sensor."),
    ("cuadrilla_operativa", "Equipos técnicos municipales por especialidad y disponibilidad."),
    ("intervencion_mantenimiento", "Tabla asociativa (resuelve N:M entre reporte_incidencia y cuadrilla_operativa)."),
]


@app.route("/modelo-datos")
@solo_admin
def modelo_datos():
    """Inspecciona en vivo las 9 tablas SQLite del MER (columnas, PK, FK y conteo real)."""
    tabla_activa = request.args.get("tabla", "reporte_incidencia")
    nombres_validos = {t[0] for t in TABLAS_MER}
    if tabla_activa not in nombres_validos:
        tabla_activa = "reporte_incidencia"

    esquema = []
    for nombre, desc in TABLAS_MER:
        total = query(f"SELECT COUNT(*) AS n FROM {nombre}", one=True)["n"]
        cols = query(f"PRAGMA table_info({nombre})")
        fks_raw = query(f"PRAGMA foreign_key_list({nombre})")
        fk_map = {fk["from"]: f"{fk['table']}.{fk['to']}" for fk in fks_raw}
        columnas = [
            {
                "nombre": c["name"],
                "tipo": c["type"] or "TEXT",
                "pk": bool(c["pk"]),
                "notnull": bool(c["notnull"]),
                "fk": fk_map.get(c["name"]),
            }
            for c in cols
        ]
        esquema.append(
            {
                "nombre": nombre,
                "descripcion": desc,
                "total": total,
                "columnas": columnas,
            }
        )

    filas_muestra = query(f"SELECT * FROM {tabla_activa} ORDER BY 1 DESC LIMIT 8")
    columnas_muestra = filas_muestra[0].keys() if filas_muestra else []
    return render_template(
        "modelo_datos.html",
        esquema=esquema,
        tabla_activa=tabla_activa,
        filas_muestra=filas_muestra,
        columnas_muestra=columnas_muestra,
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    """Inicio de sesión por correo o documento de identidad contra la tabla CIUDADANO."""
    if request.method == "POST":
        identificador = request.form.get("identificador", "").strip()
        clave = request.form.get("clave", "").strip()
        u = query(
            """SELECT * FROM ciudadano
               WHERE (correo_electronico=? OR documento_identidad=?) AND clave_acceso=?""",
            (identificador, identificador, clave),
            one=True,
        )
        if u:
            session["usuario"] = {
                "id_ciudadano": u["id_ciudadano"],
                "documento": u["documento_identidad"],
                "nombre": u["nombre_completo"],
                "correo": u["correo_electronico"],
                "telefono": u["telefono_contacto"] or "",
                "rol": u["rol"],
            }
            flash(f"Bienvenido, {u['nombre_completo']} ({u['rol']}).", "ok")
            return redirect(url_for("dashboard"))
        flash("Credenciales incorrectas. Verifica tu correo/documento y contraseña.", "error")
    return render_template("login.html")


@app.route("/registro", methods=["GET", "POST"])
def registro():
    """Vista independiente para registrar un nuevo usuario en la tabla CIUDADANO."""
    if request.method == "POST":
        doc = request.form.get("documento", "").strip()
        nombre = request.form.get("nombre", "").strip()
        correo = request.form.get("correo", "").strip()
        telefono = request.form.get("telefono", "").strip()
        rol = request.form.get("rol", "Ciudadano")
        if rol not in ("Ciudadano", "Administrador"):
            rol = "Ciudadano"
        clave = request.form.get("clave", "").strip()
        if not (doc and nombre and correo and clave):
            flash("Completa todos los campos obligatorios.", "error")
            return render_template("registro.html")
        existe = query(
            "SELECT id_ciudadano FROM ciudadano WHERE documento_identidad=? OR correo_electronico=?",
            (doc, correo),
            one=True,
        )
        if existe:
            flash("Ya existe una cuenta registrada con ese documento o correo electrónico.", "error")
            return render_template("registro.html")
        db = get_db()
        cur = db.execute(
            """INSERT INTO ciudadano
               (documento_identidad, nombre_completo, correo_electronico, telefono_contacto, rol, clave_acceso)
               VALUES (?,?,?,?,?,?)""",
            (doc, nombre, correo, telefono, rol, clave),
        )
        db.commit()
        session["usuario"] = {
            "id_ciudadano": cur.lastrowid,
            "documento": doc,
            "nombre": nombre,
            "correo": correo,
            "telefono": telefono,
            "rol": rol,
        }
        flash(f"Cuenta creada exitosamente. Bienvenido, {nombre} ({rol}).", "ok")
        return redirect(url_for("dashboard"))
    return render_template("registro.html")


@app.route("/logout")
def logout():
    session.pop("usuario", None)
    flash("Has cerrado sesión correctamente.", "ok")
    return redirect(url_for("login"))


@app.errorhandler(404)
def no_encontrado(_e):
    return render_template("404.html"), 404


init_db()

if __name__ == "__main__":
    app.run(debug=True)
