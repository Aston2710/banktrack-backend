from supabase_client import obtener_transacciones_mes, obtener_configuracion
from datetime import datetime


def verificar_limite_mes_actual() -> dict:
    """
    Revisa si el gasto del mes actual se acerca o supera el límite.
    Retorna un dict con el estado actual.
    """
    mes_actual = datetime.now().strftime("%Y-%m")
    config     = obtener_configuracion()
    limite_bs  = config.get("limite_mensual_bs") or 0
    alerta_pct = config.get("alerta_porcentaje") or 80

    if not limite_bs or limite_bs <= 0:
        return {"alerta": False, "mensaje": "Sin límite configurado"}

    transacciones = obtener_transacciones_mes(mes_actual)
    salidas       = sum(t["monto_bs"] for t in transacciones if t["tipo"] == "salida")
    porcentaje    = (salidas / limite_bs) * 100

    estado = {
        "mes":          mes_actual,
        "gastado_bs":   round(salidas, 2),
        "limite_bs":    limite_bs,
        "porcentaje":   round(porcentaje, 2),
        "alerta":       False,
        "superado":     False,
        "mensaje":      "",
    }

    if porcentaje >= 100:
        estado["superado"] = True
        estado["alerta"]   = True
        estado["mensaje"]  = f"⚠️ Límite SUPERADO: gastaste Bs. {salidas:,.2f} de Bs. {limite_bs:,.2f}"
    elif porcentaje >= alerta_pct:
        estado["alerta"]  = True
        estado["mensaje"] = f"⚠️ Alerta: {porcentaje:.1f}% del límite usado (Bs. {salidas:,.2f} de Bs. {limite_bs:,.2f})"
    else:
        estado["mensaje"] = f"✅ Gasto normal: {porcentaje:.1f}% del límite"

    print(f"[alertas] {estado['mensaje']}")
    return estado