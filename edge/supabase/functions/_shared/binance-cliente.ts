// ─── Cliente de Binance: SOLO LECTURA ─────────────────────────────────────────
// Ver control_de_gastos/docs/plan-binance.md.
//
// Garantías de este módulo:
// - Solo hace peticiones GET, y solo a las rutas de RUTAS_PERMITIDAS. No existe
//   ningún método para POST/PUT/DELETE: este código no puede operar ni retirar.
// - Nunca imprime ni devuelve la clave, el secreto, la firma ni la URL firmada.
//   Los errores solo llevan la ruta y el código/mensaje que devuelve Binance.

const BASE = "https://api.binance.com";

/** Rutas que este cliente puede consultar. Cualquier otra se rechaza. */
export const RUTAS_PERMITIDAS = new Set([
  "/api/v3/time", //                                  pública: reloj de Binance
  "/sapi/v1/account/apiRestrictions", //             permisos de la clave
  "/sapi/v1/c2c/orderMatch/listUserOrderHistory", // historial P2P
  "/sapi/v1/pay/transactions", //                    Binance Pay
  "/sapi/v1/capital/deposit/hisrec", //              depósitos de cripto
  "/sapi/v1/capital/withdraw/history", //            retiros
  "/sapi/v1/asset/wallet/balance", //                saldo por billetera
]);

const RECV_WINDOW = 5000;
const TIMEOUT_MS = 15_000;

/** Motivo por el que se detiene la sincronización. */
export type MotivoError =
  | "region" //         451: Binance bloquea la región de salida
  | "bloqueo_ip" //     418: Binance bloqueó la IP temporalmente
  | "limite" //         429: demasiadas peticiones
  | "clave_invalida" // 401 / -2014 / -2015: clave inexistente, revocada o mal copiada
  | "reloj" //          -1021: desfase de hora
  | "binance" //        cualquier otro error de Binance
  | "red"; //           sin respuesta / timeout

export class ErrorBinance extends Error {
  constructor(
    readonly motivo: MotivoError,
    readonly ruta: string,
    detalle: string,
  ) {
    super(`[binance] ${ruta}: ${motivo} (${detalle})`);
  }
}

export interface Credenciales {
  apiKey: string;
  apiSecret: string;
}

/** Lee la clave de los secrets de la función. null si falta alguna parte. */
export function credencialesDesdeEntorno(): Credenciales | null {
  const apiKey = (Deno.env.get("BINANCE_API_KEY") ?? "").trim();
  const apiSecret = (Deno.env.get("BINANCE_API_SECRET") ?? "").trim();
  if (!apiKey || !apiSecret) return null;
  return { apiKey, apiSecret };
}

/** HMAC-SHA256 en hexadecimal, como pide Binance. */
export async function firmar(secreto: string, mensaje: string): Promise<string> {
  const clave = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secreto),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const firma = await crypto.subtle.sign("HMAC", clave, new TextEncoder().encode(mensaje));
  return Array.from(new Uint8Array(firma), (b) => b.toString(16).padStart(2, "0")).join("");
}

/** Traduce una respuesta fallida de Binance a un motivo. */
export function clasificarError(status: number, codigo: number | undefined): MotivoError {
  if (status === 451) return "region";
  if (status === 418) return "bloqueo_ip";
  if (status === 429) return "limite";
  if (status === 401 || codigo === -2014 || codigo === -2015 || codigo === -2008) {
    return "clave_invalida";
  }
  if (codigo === -1021) return "reloj";
  return "binance";
}

type Params = Record<string, string | number>;

export class ClienteBinance {
  private desfaseMs = 0;

  constructor(
    private readonly cred: Credenciales,
    private readonly fetcher: typeof fetch = fetch,
  ) {}

  /** Sincroniza con el reloj de Binance (evita el error -1021). */
  async sincronizarReloj(): Promise<void> {
    const { serverTime } = await this.pedir<{ serverTime: number }>("/api/v3/time", {}, false);
    this.desfaseMs = serverTime - Date.now();
  }

  /** GET firmado a una ruta permitida. */
  get<T>(ruta: string, params: Params = {}): Promise<T> {
    return this.pedir<T>(ruta, params, true);
  }

  private async pedir<T>(ruta: string, params: Params, firmada: boolean): Promise<T> {
    if (!RUTAS_PERMITIDAS.has(ruta)) {
      throw new ErrorBinance("binance", ruta, "ruta no permitida por el cliente de solo lectura");
    }
    const consulta = new URLSearchParams();
    for (const [k, v] of Object.entries(params)) consulta.set(k, String(v));
    const cabeceras: Record<string, string> = { Accept: "application/json" };
    if (firmada) {
      consulta.set("recvWindow", String(RECV_WINDOW));
      consulta.set("timestamp", String(Date.now() + this.desfaseMs));
      consulta.set("signature", await firmar(this.cred.apiSecret, consulta.toString()));
      cabeceras["X-MBX-APIKEY"] = this.cred.apiKey;
    }

    let resp: Response;
    try {
      resp = await this.fetcher(`${BASE}${ruta}?${consulta}`, {
        method: "GET",
        headers: cabeceras,
        signal: AbortSignal.timeout(TIMEOUT_MS),
      });
    } catch (e) {
      // El mensaje de fetch puede incluir la URL firmada: no se propaga.
      throw new ErrorBinance("red", ruta, e instanceof Error ? e.name : "error de red");
    }

    const texto = await resp.text();
    let cuerpo: unknown = null;
    try {
      cuerpo = JSON.parse(texto);
    } catch {
      // cuerpo no JSON
    }
    if (!resp.ok) {
      const c = cuerpo as { code?: number; msg?: string } | null;
      const motivo = clasificarError(resp.status, c?.code);
      const detalle = `HTTP ${resp.status}${c?.code !== undefined ? `, código ${c.code}` : ""}${
        c?.msg ? `: ${String(c.msg).slice(0, 120)}` : ""
      }`;
      throw new ErrorBinance(motivo, ruta, detalle);
    }
    if (cuerpo === null) throw new ErrorBinance("binance", ruta, "respuesta no es JSON");
    return cuerpo as T;
  }
}

// ─── Verificación de permisos de la clave ────────────────────────────────────

/**
 * Campos de `apiRestrictions` que pueden estar en `true` sin peligro.
 * Cualquier otro booleano en `true` (trading, retiros, transferencias, margin,
 * futuros, opciones, o un permiso nuevo que Binance añada) hace que la clave se
 * considere insegura y la sincronización se niegue a correr.
 */
const PERMISOS_ACEPTADOS = new Set(["enableReading", "enableFixReadOnly", "ipRestrict"]);

export interface ResultadoPermisos {
  segura: boolean;
  /** Permisos peligrosos activos (vacío si es segura). */
  peligrosos: string[];
}

export function evaluarPermisos(restricciones: Record<string, unknown>): ResultadoPermisos {
  const peligrosos: string[] = [];
  for (const [campo, valor] of Object.entries(restricciones)) {
    if (valor === true && !PERMISOS_ACEPTADOS.has(campo)) peligrosos.push(campo);
  }
  if (restricciones.enableReading !== true) peligrosos.push("enableReading=false");
  return { segura: peligrosos.length === 0, peligrosos };
}
