from gmail_reader import obtener_correos_no_leidos
from parser import parsear_correo

correos = obtener_correos_no_leidos()
print(f"Total mensajes leídos: {len(correos)}\n")

for i, c in enumerate(correos, 1):
    datos = parsear_correo(c["asunto"], c["cuerpo"])
    print(f"{'─'*50}")
    print(f"Mensaje {i}")
    print(f"Asunto : {c['asunto'][:70]}")
    print(f"Tipo   : {datos.get('tipo')} / {datos.get('subtipo')}")
    print(f"Monto  : {datos.get('monto_bs')}")
    print(f"Fecha  : {datos.get('fecha')}")
    print(f"Ref    : {datos.get('referencia')}")
    print(f"cuerpo: {c["cuerpo"]}")
    print()