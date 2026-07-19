import requests
from config import DOLAR_API_URL, EURO_API_URL


def _obtener_tasa(url: str, etiqueta: str) -> float:
    """
    Consulta una tasa oficial BCV desde ve.dolarapi.com.
    Retorna el valor en Bs. o None si falla.
    """
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        tasa = data.get("promedio") or data.get("price") or data.get("valor")
        if tasa:
            return float(tasa)
        print(f"[dolar_api] Respuesta inesperada ({etiqueta}): {data}")
        return None
    except requests.RequestException as e:
        print(f"[dolar_api] Error consultando tasa {etiqueta}: {e}")
        return None


def obtener_tasa_bcv() -> float:
    """Tasa oficial USD/Bs. Retorna None si falla."""
    return _obtener_tasa(DOLAR_API_URL, "dólar")


def obtener_tasa_euro() -> float:
    """Tasa oficial EUR/Bs. Retorna None si falla o si EURO_API_URL no está configurada."""
    if not EURO_API_URL:
        print("[dolar_api] EURO_API_URL no configurada — se omite conversión EUR")
        return None
    return _obtener_tasa(EURO_API_URL, "euro")
