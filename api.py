from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import os

app    = FastAPI(title="BankTrack API", version="1.0.0")
bearer = HTTPBearer()

API_KEY = os.getenv("API_KEY")

# CORS — permite que la app móvil se conecte
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "PATCH"],
    allow_headers=["Authorization", "Content-Type"],
)

def verificar_token(credentials: HTTPAuthorizationCredentials = Depends(bearer)):
    if credentials.credentials != API_KEY:
        raise HTTPException(status_code=401, detail="No autorizado")


# ── Health check — para verificar que la API está viva ────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


# ── Transacciones ──────────────────────────────────────────────────────────────
@app.get("/transacciones/{mes}")
def obtener_transacciones(mes: str, _=Depends(verificar_token)):
    """Retorna todas las transacciones de un mes. Formato: 2026-06"""
    from supabase_client import obtener_transacciones_mes
    return obtener_transacciones_mes(mes)


@app.get("/transacciones/{mes}/subtipo/{subtipo}")
def obtener_transacciones_por_subtipo(mes: str, subtipo: str, _=Depends(verificar_token)):
    """Filtra transacciones por subtipo: enviado, recibido, tarjeta, etc."""
    from supabase_client import obtener_transacciones_mes
    todas = obtener_transacciones_mes(mes)
    return [t for t in todas if t.get("subtipo") == subtipo]


@app.patch("/transacciones/{id}")
def actualizar_transaccion(id: str, body: dict, _=Depends(verificar_token)):
    """
    Permite editar campos no sensibles: categoria, nota, etiquetas.
    El monto nunca se puede modificar.
    """
    from supabase_client import _cliente

    # Campos que el usuario puede editar
    campos_editables = {"categoria", "nota", "etiquetas"}
    campos_recibidos = set(body.keys())
    campos_no_permitidos = campos_recibidos - campos_editables

    if campos_no_permitidos:
        raise HTTPException(
            status_code=400,
            detail=f"Campos no editables: {campos_no_permitidos}"
        )

    try:
        _cliente.table("transacciones").update(body).eq("id", id).execute()
        return {"ok": True, "id": id, "actualizado": body}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Resumen mensual ────────────────────────────────────────────────────────────
@app.get("/resumen/{mes}")
def obtener_resumen(mes: str, _=Depends(verificar_token)):
    """Totales del mes: entradas, salidas, comisiones, balance."""
    from supabase_client import obtener_transacciones_mes
    transacciones = obtener_transacciones_mes(mes)

    entradas   = sum(t["monto_bs"] for t in transacciones if t["tipo"] == "entrada")
    salidas    = sum(t["monto_bs"] for t in transacciones if t["tipo"] == "salida")
    comisiones = sum(t.get("comision_bs") or 0 for t in transacciones)
    tasas      = [t["tasa_dolar"] for t in transacciones if t.get("tasa_dolar")]
    tasa_prom  = round(sum(tasas) / len(tasas), 4) if tasas else None

    return {
        "mes":              mes,
        "entradas_bs":      round(entradas, 2),
        "salidas_bs":       round(salidas, 2),
        "balance_bs":       round(entradas - salidas, 2),
        "comisiones_bs":    round(comisiones, 2),
        "pct_comisiones":   round(comisiones / salidas * 100, 2) if salidas > 0 else 0,
        "entradas_usd":     round(entradas / tasa_prom, 2) if tasa_prom else None,
        "salidas_usd":      round(salidas / tasa_prom, 2) if tasa_prom else None,
        "balance_usd":      round((entradas - salidas) / tasa_prom, 2) if tasa_prom else None,
        "tasa_promedio":    tasa_prom,
        "total_movimientos": len(transacciones),
    }


# ── Estadísticas ───────────────────────────────────────────────────────────────
@app.get("/estadisticas/{mes}")
def obtener_estadisticas(mes: str, _=Depends(verificar_token)):
    """Desglose de gastos por subtipo para gráficas."""
    from supabase_client import obtener_transacciones_mes
    transacciones = obtener_transacciones_mes(mes)

    subtipos = {}
    for t in transacciones:
        if t["tipo"] in ("salida", "rechazado"):
            s = t.get("subtipo", "desconocido")
            subtipos[s] = subtipos.get(s, 0) + (t.get("monto_bs") or 0)

    return {
        "mes":     mes,
        "por_subtipo": [
            {"subtipo": k, "total_bs": round(v, 2)}
            for k, v in sorted(subtipos.items(), key=lambda x: x[1], reverse=True)
        ]
    }


# ── Configuración ──────────────────────────────────────────────────────────────
@app.get("/configuracion")
def obtener_configuracion(_=Depends(verificar_token)):
    from supabase_client import obtener_configuracion
    return obtener_configuracion()


@app.patch("/configuracion/{id}")
def actualizar_configuracion(id: str, body: dict, _=Depends(verificar_token)):
    from supabase_client import _cliente
    campos_editables = {"limite_mensual_bs", "limite_mensual_usd",
                        "alerta_porcentaje", "moneda_principal"}
    campos_no_permitidos = set(body.keys()) - campos_editables
    if campos_no_permitidos:
        raise HTTPException(status_code=400,
                            detail=f"Campos no editables: {campos_no_permitidos}")
    try:
        _cliente.table("configuracion").update(body).eq("id", id).execute()
        return {"ok": True, "actualizado": body}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Cierres mensuales ──────────────────────────────────────────────────────────
@app.get("/cierres")
def obtener_cierres(_=Depends(verificar_token)):
    from supabase_client import _cliente
    try:
        res = _cliente.table("cierres_mensuales").select("*").order("mes", desc=True).execute()
        return res.data or []
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))