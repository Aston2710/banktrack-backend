from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY
from datetime import datetime

_cliente: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def existe_referencia(referencia: str) -> bool:
    """Verifica si ya existe una transacción con esa referencia."""
    if not referencia:
        return False
    try:
        res = (_cliente.table("transacciones")
               .select("id")
               .eq("referencia", referencia)
               .execute())
        return len(res.data) > 0
    except Exception as e:
        print(f"[supabase] Error verificando referencia: {e}")
        return False

def insertar_transaccion(datos: dict) -> bool:
    """
    Inserta una transacción. Si el email_id ya existe la ignora.
    Retorna True si se insertó, False si ya existía o hubo error.
    """
    try:
        _cliente.table("transacciones").insert(datos).execute()
        print(f"[supabase] Transacción insertada: {datos.get('referencia')}")
        return True
    except Exception as e:
        mensaje = str(e)
        if "duplicate" in mensaje.lower() or "unique" in mensaje.lower():
            print(f"[supabase] Ya existe: {datos.get('email_id')} — ignorado")
            return False
        print(f"[supabase] Error insertando: {e}")
        return False


def obtener_transacciones_mes(mes: str) -> list:
    """
    mes formato: '2026-05'
    """
    try:
        res = (_cliente.table("transacciones")
               .select("*")
               .eq("mes_corte", mes)
               .order("fecha", desc=True)
               .execute())
        return res.data or []
    except Exception as e:
        print(f"[supabase] Error consultando mes {mes}: {e}")
        return []


def obtener_configuracion() -> dict:
    try:
        res = _cliente.table("configuracion").select("*").limit(1).execute()
        return res.data[0] if res.data else {}
    except Exception as e:
        print(f"[supabase] Error obteniendo configuración: {e}")
        return {}


def guardar_cierre_mensual(mes: str) -> bool:
    """
    Genera y guarda el snapshot del mes indicado.
    """
    try:
        transacciones = obtener_transacciones_mes(mes)
        if not transacciones:
            print(f"[supabase] Sin transacciones para cerrar mes {mes}")
            return False

        entradas_bs  = sum(t["monto_bs"] for t in transacciones if t["tipo"] == "entrada")
        salidas_bs   = sum(t["monto_bs"] for t in transacciones if t["tipo"] == "salida")
        entradas_usd = sum(t.get("monto_usd") or 0 for t in transacciones if t["tipo"] == "entrada")
        salidas_usd  = sum(t.get("monto_usd") or 0 for t in transacciones if t["tipo"] == "salida")
        comisiones   = sum(t.get("comision_bs") or 0 for t in transacciones)
        tasas        = [t["tasa_dolar"] for t in transacciones if t.get("tasa_dolar")]
        tasa_prom    = round(sum(tasas) / len(tasas), 4) if tasas else None
        pct_comision = round((comisiones / salidas_bs * 100), 4) if salidas_bs > 0 else 0

        cierre = {
            "mes":                  mes,
            "total_entradas_bs":    round(entradas_bs, 2),
            "total_salidas_bs":     round(salidas_bs, 2),
            "total_entradas_usd":   round(entradas_usd, 4),
            "total_salidas_usd":    round(salidas_usd, 4),
            "total_comisiones_bs":  round(comisiones, 2),
            "porcentaje_comisiones": pct_comision,
            "tasa_promedio_mes":    tasa_prom,
            "cerrado_en":           datetime.utcnow().isoformat(),
        }

        _cliente.table("cierres_mensuales").upsert(cierre).execute()
        print(f"[supabase] Cierre mensual guardado: {mes}")
        return True
    except Exception as e:
        print(f"[supabase] Error guardando cierre: {e}")
        return False