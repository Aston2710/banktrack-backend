# api.py — se agrega al proyecto existente
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os

app    = FastAPI()
bearer = HTTPBearer()

API_KEY = os.getenv("API_KEY")  # clave que solo tú y la app conocen

def verificar_token(credentials: HTTPAuthorizationCredentials = Depends(bearer)):
    if credentials.credentials != API_KEY:
        raise HTTPException(status_code=401, detail="No autorizado")

@app.get("/transacciones/{mes}")
def obtener_transacciones(mes: str, _=Depends(verificar_token)):
    from supabase_client import obtener_transacciones_mes
    return obtener_transacciones_mes(mes)

@app.get("/resumen/{mes}")
def obtener_resumen(mes: str, _=Depends(verificar_token)):
    from supabase_client import obtener_transacciones_mes
    transacciones = obtener_transacciones_mes(mes)
    salidas   = sum(t["monto_bs"] for t in transacciones if t["tipo"] == "salida")
    entradas  = sum(t["monto_bs"] for t in transacciones if t["tipo"] == "entrada")
    comisiones = sum(t["comision_bs"] or 0 for t in transacciones)
    return {
        "mes":        mes,
        "entradas":   entradas,
        "salidas":    salidas,
        "comisiones": comisiones,
        "balance":    entradas - salidas
    }