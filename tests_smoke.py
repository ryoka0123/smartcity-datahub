import os, sys
sys.path.insert(0, r"C:\Users\jonat\.gemini\antigravity\scratch\smartcity-datahub")
os.chdir(r"C:\Users\jonat\.gemini\antigravity\scratch\smartcity-datahub")
import app as m

c = m.app.test_client()
for url in ["/", "/reportes", "/reportes?estado=Pendiente", "/reportes/nuevo", "/reportes/1",
            "/reportes/2", "/sensores", "/cuadrillas", "/reportes/999"]:
    r = c.get(url)
    print(url, r.status_code)

r = c.post("/reportes/nuevo", data={"documento": "999", "nombre": "Test", "correo": "t@t.co",
    "id_zona": 1, "id_categoria": 1, "descripcion": "prueba", "latitud": "7.12", "longitud": "-73.11"})
print("crear", r.status_code, r.headers.get("Location"))
r = c.post("/reportes/2/asignar", data={"id_cuadrilla": 1, "diagnostico": "x"})
print("asignar", r.status_code)
r = c.post("/intervenciones/3/cerrar", data={"costo": "50000"})
print("cerrar", r.status_code)
r = c.post("/sensores/1/simular")
print("simular", r.status_code)
r = c.get("/reportes/2")
print("detalle tras cerrar", r.status_code, b"Resuelto" in r.data)
