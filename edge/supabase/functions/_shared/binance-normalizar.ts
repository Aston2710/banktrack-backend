// ─── Normalización de respuestas de Binance → filas de binance_operaciones ───
// Funciones puras (sin red ni BD) para poder probarlas.
// Regla: solo operaciones FINALIZADAS. Pendientes, canceladas o en apelación se
// ignoran; si terminan completándose, se leen en un ciclo posterior (los ciclos
// se solapan unos días, ver sincronizar-binance).

export type TipoOperacion = "p2p" | "pay" | "deposito" | "retiro";

export interface Operacion {
  tipo: TipoOperacion;
  id_binance: string;
  fecha: string; // ISO UTC
  direccion: "entrada" | "salida";
  activo: string;
  cantidad: string; // decimal en texto: nunca pasa por float
  comision: string;
  monto_fiat: string | null;
  fiat: string | null;
  datos: Record<string, unknown>;
}

/** Decimal en texto, validado. Devuelve el valor absoluto. Lanza si no es un número. */
export function decimal(valor: unknown, campo: string): string {
  const s = String(valor ?? "").trim();
  if (!/^-?\d+(\.\d+)?$/.test(s)) throw new Error(`valor no numérico en ${campo}: ${s.slice(0, 30)}`);
  return s.startsWith("-") ? s.slice(1) : s;
}

function esNegativo(valor: unknown): boolean {
  return String(valor ?? "").trim().startsWith("-");
}

function fechaIso(ms: unknown, campo: string): string {
  const n = Number(ms);
  if (!Number.isFinite(n) || n <= 0) throw new Error(`fecha inválida en ${campo}`);
  return new Date(n).toISOString();
}

/** Binance da algunas fechas como "2026-10-12 11:12:02" en UTC. */
export function fechaTextoUtc(texto: unknown, campo: string): string {
  const s = String(texto ?? "").trim();
  if (!/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/.test(s)) throw new Error(`fecha inválida en ${campo}`);
  return new Date(`${s.replace(" ", "T")}Z`).toISOString();
}

// ─── P2P ─────────────────────────────────────────────────────────────────────

export interface OrdenP2P {
  orderNumber: string;
  tradeType: "BUY" | "SELL";
  asset: string;
  fiat: string;
  amount: string;
  totalPrice: string;
  commission?: string;
  orderStatus: string;
  createTime: number;
  [k: string]: unknown;
}

export function normalizarP2P(o: OrdenP2P): Operacion | null {
  if (o.orderStatus !== "COMPLETED") return null;
  if (o.tradeType !== "BUY" && o.tradeType !== "SELL") throw new Error(`tradeType desconocido: ${o.tradeType}`);
  return {
    tipo: "p2p",
    id_binance: String(o.orderNumber),
    fecha: fechaIso(o.createTime, "p2p.createTime"),
    direccion: o.tradeType === "BUY" ? "entrada" : "salida",
    activo: String(o.asset),
    cantidad: decimal(o.amount, "p2p.amount"),
    comision: o.commission === undefined ? "0" : decimal(o.commission, "p2p.commission"),
    monto_fiat: decimal(o.totalPrice, "p2p.totalPrice"),
    fiat: String(o.fiat),
    datos: o,
  };
}

// ─── Binance Pay ─────────────────────────────────────────────────────────────

export interface TransaccionPay {
  transactionId: string;
  transactionTime: number;
  amount: string; // negativo = enviado
  currency: string;
  orderType?: string;
  [k: string]: unknown;
}

/** El historial de Pay solo lista transacciones ya liquidadas. */
export function normalizarPay(t: TransaccionPay): Operacion {
  return {
    tipo: "pay",
    id_binance: String(t.transactionId),
    fecha: fechaIso(t.transactionTime, "pay.transactionTime"),
    direccion: esNegativo(t.amount) ? "salida" : "entrada",
    activo: String(t.currency),
    cantidad: decimal(t.amount, "pay.amount"),
    comision: "0",
    monto_fiat: null,
    fiat: null,
    datos: t,
  };
}

// ─── Depósitos ───────────────────────────────────────────────────────────────

export interface Deposito {
  id: string;
  amount: string;
  coin: string;
  status: number; // 1 = acreditado
  insertTime: number;
  [k: string]: unknown;
}

export function normalizarDeposito(d: Deposito): Operacion | null {
  if (d.status !== 1) return null;
  return {
    tipo: "deposito",
    id_binance: String(d.id),
    fecha: fechaIso(d.insertTime, "deposito.insertTime"),
    direccion: "entrada",
    activo: String(d.coin),
    cantidad: decimal(d.amount, "deposito.amount"),
    comision: "0",
    monto_fiat: null,
    fiat: null,
    datos: d,
  };
}

// ─── Retiros ─────────────────────────────────────────────────────────────────

export interface Retiro {
  id: string;
  amount: string;
  transactionFee?: string;
  coin: string;
  status: number; // 6 = completado
  applyTime: string; // "YYYY-MM-DD HH:mm:ss" UTC
  [k: string]: unknown;
}

export function normalizarRetiro(r: Retiro): Operacion | null {
  if (r.status !== 6) return null;
  return {
    tipo: "retiro",
    id_binance: String(r.id),
    fecha: fechaTextoUtc(r.applyTime, "retiro.applyTime"),
    direccion: "salida",
    activo: String(r.coin),
    cantidad: decimal(r.amount, "retiro.amount"),
    comision: r.transactionFee === undefined ? "0" : decimal(r.transactionFee, "retiro.transactionFee"),
    monto_fiat: null,
    fiat: null,
    datos: r,
  };
}

// ─── Ventanas de tiempo ──────────────────────────────────────────────────────

/** Parte [desde, hasta) en ventanas de como máximo `tamanoMs`. */
export function ventanas(desde: number, hasta: number, tamanoMs: number): Array<[number, number]> {
  if (!(tamanoMs > 0)) throw new Error("tamaño de ventana inválido");
  const res: Array<[number, number]> = [];
  for (let ini = desde; ini < hasta; ini += tamanoMs) res.push([ini, Math.min(ini + tamanoMs, hasta)]);
  return res;
}
