// ─── Edge Function: sincronizar-binance (Etapa A: lectura en seco) ───────────
// Ver control_de_gastos/docs/plan-binance.md.
//
// Lee el historial de Binance con una clave de SOLO LECTURA y lo copia en
// `binance_operaciones`. No toca `ahorro_movimientos` (eso es la Etapa C).
// Ante cualquier duda se detiene, deja el motivo en `binance_sincronizacion` y
// no reintenta en bucle.

import type { SupabaseClient } from "@supabase/supabase-js";
import { getClient } from "../_shared/binance-db.ts";
import {
  ClienteBinance,
  credencialesDesdeEntorno,
  ErrorBinance,
  evaluarPermisos,
} from "../_shared/binance-cliente.ts";
import {
  type Deposito,
  normalizarDeposito,
  normalizarP2P,
  normalizarPay,
  normalizarRetiro,
  type Operacion,
  type OrdenP2P,
  type Retiro,
  type TransaccionPay,
  ventanas,
} from "../_shared/binance-normalizar.ts";

const CRON_KEY = Deno.env.get("CRON_KEY") ?? "";
/** Regiones desde las que Binance responde (verificado 2026-11-03). */
const REGIONES_PERMITIDAS = new Set(["sa-east-1"]);

const DIA = 24 * 60 * 60 * 1000;
/** Cada ciclo relee los últimos días por si una operación terminó después de leída. */
const SOLAPE_MS = 3 * DIA;
/** Tope de ventanas por fuente y ciclo: el relleno del historial viejo se reparte en varios ciclos. */
const MAX_VENTANAS_POR_CICLO = 4;
const PAUSA_MS = 250;

const json = (cuerpo: unknown, status = 200) =>
  new Response(JSON.stringify(cuerpo), { status, headers: { "Content-Type": "application/json" } });

function autorizado(req: Request): boolean {
  const recibido = (req.headers.get("Authorization") ?? "").replace(/^Bearer\s+/i, "");
  if (!CRON_KEY || recibido.length !== CRON_KEY.length) return false;
  let diferencia = 0;
  for (let i = 0; i < CRON_KEY.length; i++) diferencia |= recibido.charCodeAt(i) ^ CRON_KEY.charCodeAt(i);
  return diferencia === 0;
}

const pausa = () => new Promise((r) => setTimeout(r, PAUSA_MS));

// ─── Lectura por fuente ──────────────────────────────────────────────────────

interface Fuente {
  clave: string; // clave en `cursores`
  ventanaMs: number;
  leer: (b: ClienteBinance, desde: number, hasta: number) => Promise<Operacion[]>;
}

function exigirLista(valor: unknown, ruta: string): unknown[] {
  if (!Array.isArray(valor)) throw new ErrorBinance("binance", ruta, "formato inesperado");
  return valor;
}

function leerP2P(tradeType: "BUY" | "SELL") {
  return async (b: ClienteBinance, desde: number, hasta: number) => {
    const ruta = "/sapi/v1/c2c/orderMatch/listUserOrderHistory";
    const ops: Operacion[] = [];
    for (let page = 1; page <= 50; page++) {
      const r = await b.get<{ data?: unknown }>(ruta, {
        tradeType,
        startTimestamp: desde,
        endTimestamp: hasta - 1,
        page,
        rows: 100,
      });
      const datos = exigirLista(r.data, ruta) as OrdenP2P[];
      for (const o of datos) {
        const op = normalizarP2P(o);
        if (op) ops.push(op);
      }
      if (datos.length < 100) return ops;
      await pausa();
    }
    throw new ErrorBinance("binance", ruta, "más de 5000 órdenes en una ventana");
  };
}

async function leerPay(b: ClienteBinance, desde: number, hasta: number): Promise<Operacion[]> {
  const ruta = "/sapi/v1/pay/transactions";
  const r = await b.get<{ data?: unknown }>(ruta, { startTime: desde, endTime: hasta - 1, limit: 100 });
  const datos = exigirLista(r.data, ruta) as TransaccionPay[];
  if (datos.length < 100) return datos.map(normalizarPay);
  // Sin paginación en este endpoint: si viene lleno, se parte la ventana en dos.
  if (hasta - desde <= 60 * 60 * 1000) throw new ErrorBinance("binance", ruta, "más de 100 pagos en una hora");
  const medio = Math.floor((desde + hasta) / 2);
  await pausa();
  const a = await leerPay(b, desde, medio);
  await pausa();
  return [...a, ...(await leerPay(b, medio, hasta))];
}

function leerConOffset<T>(ruta: string, normalizar: (x: T) => Operacion | null) {
  return async (b: ClienteBinance, desde: number, hasta: number) => {
    const ops: Operacion[] = [];
    for (let offset = 0; offset < 20_000; offset += 1000) {
      const datos = exigirLista(
        await b.get<unknown>(ruta, { startTime: desde, endTime: hasta - 1, offset, limit: 1000 }),
        ruta,
      ) as T[];
      for (const x of datos) {
        const op = normalizar(x);
        if (op) ops.push(op);
      }
      if (datos.length < 1000) return ops;
      await pausa();
    }
    throw new ErrorBinance("binance", ruta, "demasiados registros en una ventana");
  };
}

const FUENTES: Fuente[] = [
  { clave: "p2p_compra", ventanaMs: 30 * DIA, leer: leerP2P("BUY") },
  { clave: "p2p_venta", ventanaMs: 30 * DIA, leer: leerP2P("SELL") },
  { clave: "pay", ventanaMs: 30 * DIA, leer: leerPay },
  { clave: "deposito", ventanaMs: 89 * DIA, leer: leerConOffset<Deposito>("/sapi/v1/capital/deposit/hisrec", normalizarDeposito) },
  { clave: "retiro", ventanaMs: 89 * DIA, leer: leerConOffset<Retiro>("/sapi/v1/capital/withdraw/history", normalizarRetiro) },
];

// ─── Persistencia ────────────────────────────────────────────────────────────

async function guardar(db: SupabaseClient, ops: Operacion[]): Promise<number> {
  if (ops.length === 0) return 0;
  // ON CONFLICT DO NOTHING: releer una operación nunca la duplica ni la modifica.
  const { data, error } = await db
    .from("binance_operaciones")
    .upsert(ops, { onConflict: "tipo,id_binance", ignoreDuplicates: true })
    .select("id");
  if (error) throw new Error(`no se pudo guardar en binance_operaciones: ${error.message}`);
  return data?.length ?? 0;
}

interface Estado {
  etapa: string;
  desde: string;
  cursores: Record<string, number>;
  fallos_seguidos: number;
}

async function registrar(db: SupabaseClient, cambios: Record<string, unknown>) {
  const { error } = await db.from("binance_sincronizacion").update(cambios).eq("id", 1);
  if (error) console.error(`[binance] no se pudo registrar el estado: ${error.message}`);
}

// ─── Ciclo ───────────────────────────────────────────────────────────────────

Deno.serve(async (req) => {
  if (!autorizado(req)) return json({ ok: false, error: "no autorizado" }, 401);

  const region = Deno.env.get("SB_REGION") ?? "";
  const db = getClient();

  if (!REGIONES_PERMITIDAS.has(region)) {
    // Fuera de región no se toma el bloqueo ni se llama a Binance.
    await registrar(db, {
      ultima_ejecucion: new Date().toISOString(),
      resultado: "region",
      mensaje: `La función corrió en "${region || "desconocida"}"; debe invocarse con x-region: sa-east-1.`,
    });
    return json({ ok: false, motivo: "region", region });
  }

  const { data: tomado, error: errBloqueo } = await db.rpc("binance_tomar_bloqueo");
  if (errBloqueo) return json({ ok: false, error: `bloqueo: ${errBloqueo.message}` }, 500);
  if (tomado !== true) return json({ ok: false, motivo: "inactiva o ya en curso" });

  const inicio = Date.now();
  let estado: Estado | null = null;
  const cursores: Record<string, number> = {};
  const nuevos: Record<string, number> = {};

  try {
    const { data, error } = await db
      .from("binance_sincronizacion")
      .select("etapa, desde, cursores, fallos_seguidos")
      .eq("id", 1)
      .single();
    if (error || !data) throw new Error(`no se pudo leer binance_sincronizacion: ${error?.message}`);
    estado = data as Estado;
    Object.assign(cursores, estado.cursores ?? {});

    if (estado.etapa !== "A") {
      throw new Error(`etapa ${estado.etapa} no implementada todavía; solo existe la A (lectura en seco)`);
    }

    const cred = credencialesDesdeEntorno();
    if (!cred) {
      await registrar(db, {
        ultima_ejecucion: new Date().toISOString(),
        resultado: "sin_clave",
        mensaje: "Faltan los secrets BINANCE_API_KEY / BINANCE_API_SECRET.",
      });
      return json({ ok: false, motivo: "sin_clave" });
    }

    const binance = new ClienteBinance(cred);
    await binance.sincronizarReloj();

    // 1. La clave debe ser de solo lectura. Si no, no se lee nada.
    const restricciones = await binance.get<Record<string, unknown>>("/sapi/v1/account/apiRestrictions");
    const permisos = evaluarPermisos(restricciones);
    if (!permisos.segura) {
      await registrar(db, {
        ultima_ejecucion: new Date().toISOString(),
        resultado: "clave_insegura",
        mensaje: `La clave tiene permisos de más (${permisos.peligrosos.join(", ")}). ` +
          "Bórrala en Binance y crea una solo con 'Enable Reading'. No se leyó nada.",
        fallos_seguidos: (estado.fallos_seguidos ?? 0) + 1,
      });
      console.error(`[binance] clave insegura: ${permisos.peligrosos.join(", ")}`);
      return json({ ok: false, motivo: "clave_insegura" });
    }

    // 2. Historial por fuente.
    const desdeConfig = new Date(estado.desde).getTime();
    const ahora = Date.now();
    for (const f of FUENTES) {
      const cursor = cursores[f.clave];
      const desde = Math.max(desdeConfig, cursor ? cursor - SOLAPE_MS : desdeConfig);
      nuevos[f.clave] = 0;
      for (const [ini, fin] of ventanas(desde, ahora, f.ventanaMs).slice(0, MAX_VENTANAS_POR_CICLO)) {
        const ops = await f.leer(binance, ini, fin);
        nuevos[f.clave] += await guardar(db, ops);
        cursores[f.clave] = fin; // solo avanza cuando la ventana quedó guardada
        await pausa();
      }
    }

    // 3. Saldo real para la conciliación (valorado en USDT por Binance).
    const billeteras = await binance.get<unknown>("/sapi/v1/asset/wallet/balance", { quoteAsset: "USDT" });
    const saldo = exigirLista(billeteras, "/sapi/v1/asset/wallet/balance")
      .reduce((s: number, w) => s + Number((w as { balance?: string }).balance ?? 0), 0);

    const resumen = Object.entries(nuevos).map(([k, n]) => `${k}: ${n}`).join(", ");
    await registrar(db, {
      ultima_ejecucion: new Date().toISOString(),
      ultimo_exito: new Date().toISOString(),
      resultado: "ok",
      mensaje: `Nuevas → ${resumen}`,
      fallos_seguidos: 0,
      cursores,
      saldo_binance_usdt: saldo.toFixed(8),
      saldo_en: new Date().toISOString(),
    });
    console.log(`[binance] ok en ${Date.now() - inicio} ms · nuevas → ${resumen}`);
    return json({ ok: true, nuevos });
  } catch (e) {
    const motivo = e instanceof ErrorBinance ? e.motivo : "error";
    const mensaje = e instanceof Error ? e.message : String(e);
    console.error(`[binance] ${mensaje}`);
    await registrar(db, {
      ultima_ejecucion: new Date().toISOString(),
      resultado: motivo,
      mensaje: mensaje.slice(0, 500),
      fallos_seguidos: (estado?.fallos_seguidos ?? 0) + 1,
      cursores, // conserva lo que sí se guardó
    });
    return json({ ok: false, motivo });
  } finally {
    const { error } = await db.rpc("binance_soltar_bloqueo");
    if (error) console.error(`[binance] no se pudo soltar el bloqueo: ${error.message}`);
  }
});
