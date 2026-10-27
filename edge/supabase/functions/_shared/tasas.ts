// ─── Consulta de tasas de cambio BCV ──────────────────────────────────────────
// Traducción fiel de dolar_api.py

const DOLAR_API_URL = Deno.env.get("DOLAR_API_URL") ?? "";
const EURO_API_URL  = Deno.env.get("EURO_API_URL") ?? "";

/**
 * Consulta una tasa oficial BCV desde ve.dolarapi.com.
 * Retorna el valor en Bs. o null si falla.
 */
async function _obtenerTasa(url: string, etiqueta: string): Promise<number | null> {
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 10000);

    const response = await fetch(url, { signal: controller.signal });
    clearTimeout(timeout);

    if (!response.ok) {
      console.log(`[dolar_api] Error HTTP ${response.status} consultando tasa ${etiqueta}`);
      return null;
    }

    const data = await response.json();
    const tasa = data.promedio ?? data.price ?? data.valor;

    if (tasa) {
      return parseFloat(String(tasa));
    }

    console.log(`[dolar_api] Respuesta inesperada (${etiqueta}):`, data);
    return null;
  } catch (e) {
    console.log(`[dolar_api] Error consultando tasa ${etiqueta}: ${e}`);
    return null;
  }
}

/** Tasa oficial USD/Bs. Retorna null si falla. */
export async function obtenerTasaBcv(): Promise<number | null> {
  return _obtenerTasa(DOLAR_API_URL, "dólar");
}

/** Tasa oficial EUR/Bs. Retorna null si falla o si EURO_API_URL no está configurada. */
export async function obtenerTasaEuro(): Promise<number | null> {
  if (!EURO_API_URL) {
    console.log("[dolar_api] EURO_API_URL no configurada — se omite conversión EUR");
    return null;
  }
  return _obtenerTasa(EURO_API_URL, "euro");
}
