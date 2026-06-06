import requests
from config import DOLAR_API_URL

def obtener_tasa_bcv() -> float:
    """
    Consulta la tasa BCV desde ve.dolarapi.com
    Retorna el valor del dólar en Bs.
    Si falla retorna None.
    """
    try:
        response = requests.get(DOLAR_API_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        #print(f"{data}")

        tasa = data.get("promedio") or data.get("price") or data.get("valor")
        if tasa:
            return float(tasa)
        print(f"[dolar_api] Respuesta inesperada: {data}")
        return None
    except requests.RequestException as e:
        print(f"[dolar_api] Error consultando tasa: {e}")
        return None