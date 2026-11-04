import { assert, assertEquals, assertRejects, assertThrows } from "jsr:@std/assert@1";
import {
  ClienteBinance,
  clasificarError,
  ErrorBinance,
  evaluarPermisos,
  firmar,
} from "../_shared/binance-cliente.ts";
import {
  decimal,
  fechaTextoUtc,
  normalizarDeposito,
  normalizarP2P,
  normalizarPay,
  normalizarRetiro,
  ventanas,
} from "../_shared/binance-normalizar.ts";

// ─── Firma ───────────────────────────────────────────────────────────────────

Deno.test("firma HMAC-SHA256 igual al ejemplo oficial de Binance", async () => {
  // Ejemplo de la documentación de Binance (SIGNED endpoint examples).
  const secreto = "NhqPtmdSJYdKjVHjA7PZj4Mge3R5YNiP1e3UZjInClVN65XAbvqqM6A7H5fATj0j";
  const query =
    "symbol=LTCBTC&side=BUY&type=LIMIT&timeInForce=GTC&quantity=1&price=0.1&recvWindow=5000&timestamp=1499827319559";
  assertEquals(
    await firmar(secreto, query),
    "c8db56825ae71d6d79447849e617115f4a920fa2acdcab2b053c4b2838bd6b71",
  );
});

// ─── Permisos de la clave ────────────────────────────────────────────────────

const SOLO_LECTURA = {
  ipRestrict: false,
  createTime: 1698645219000,
  enableReading: true,
  enableWithdrawals: false,
  enableInternalTransfer: false,
  enableMargin: false,
  enableFutures: false,
  permitsUniversalTransfer: false,
  enableVanillaOptions: false,
  enableFixApiTrade: false,
  enableFixReadOnly: false,
  enableSpotAndMarginTrading: false,
  enablePortfolioMarginTrading: false,
};

Deno.test("clave de solo lectura: segura", () => {
  assertEquals(evaluarPermisos(SOLO_LECTURA), { segura: true, peligrosos: [] });
});

for (const permiso of [
  "enableWithdrawals",
  "enableSpotAndMarginTrading",
  "enableInternalTransfer",
  "permitsUniversalTransfer",
  "enableMargin",
  "enableFutures",
  "enableFixApiTrade",
]) {
  Deno.test(`clave con ${permiso}: insegura`, () => {
    const r = evaluarPermisos({ ...SOLO_LECTURA, [permiso]: true });
    assertEquals(r.segura, false);
    assert(r.peligrosos.includes(permiso));
  });
}

Deno.test("un permiso nuevo desconocido en true también la vuelve insegura", () => {
  assertEquals(evaluarPermisos({ ...SOLO_LECTURA, enableAlgoNuevo: true }).segura, false);
});

Deno.test("sin enableReading: insegura", () => {
  assertEquals(evaluarPermisos({ ...SOLO_LECTURA, enableReading: false }).segura, false);
});

// ─── Cliente: rutas, método y secretos ───────────────────────────────────────

const CRED = { apiKey: "CLAVE-PUBLICA-DE-PRUEBA", apiSecret: "SECRETO-DE-PRUEBA-NO-DEBE-SALIR" };

Deno.test("rechaza rutas fuera de la lista (p. ej. retirar) sin llamar a la red", async () => {
  let llamadas = 0;
  const cliente = new ClienteBinance(CRED, (() => {
    llamadas++;
    return Promise.resolve(new Response("{}"));
  }) as typeof fetch);
  await assertRejects(() => cliente.get("/sapi/v1/capital/withdraw/apply"), ErrorBinance);
  await assertRejects(() => cliente.get("/api/v3/order"), ErrorBinance);
  assertEquals(llamadas, 0);
});

Deno.test("siempre usa GET, firma y manda la clave solo en la cabecera", async () => {
  let metodo = "";
  let url = "";
  let cabecera = "";
  const cliente = new ClienteBinance(CRED, ((u: string, init?: RequestInit) => {
    metodo = init?.method ?? "";
    url = u;
    cabecera = (init?.headers as Record<string, string>)["X-MBX-APIKEY"];
    return Promise.resolve(new Response("[]"));
  }) as typeof fetch);
  await cliente.get("/sapi/v1/capital/deposit/hisrec", { limit: 10 });
  assertEquals(metodo, "GET");
  assertEquals(cabecera, CRED.apiKey);
  assert(url.includes("signature="));
  assert(!url.includes(CRED.apiSecret));
  assert(!url.includes(CRED.apiKey));
});

Deno.test("los errores no filtran clave, secreto ni URL firmada", async () => {
  const cliente = new ClienteBinance(CRED, (() =>
    Promise.resolve(
      new Response(JSON.stringify({ code: -2015, msg: "Invalid API-key, IP, or permissions for action." }), {
        status: 401,
      }),
    )) as typeof fetch);
  const e = await assertRejects(() => cliente.get("/sapi/v1/pay/transactions"), ErrorBinance);
  assertEquals(e.motivo, "clave_invalida");
  for (const prohibido of [CRED.apiKey, CRED.apiSecret, "signature", "timestamp="]) {
    assert(!e.message.includes(prohibido), `el error contiene ${prohibido}`);
  }
});

Deno.test("un fallo de red no propaga el mensaje original (que puede traer la URL)", async () => {
  const cliente = new ClienteBinance(CRED, (() =>
    Promise.reject(new TypeError(`fallo en https://api.binance.com/x?signature=abc&k=${CRED.apiKey}`))) as typeof fetch);
  const e = await assertRejects(() => cliente.get("/sapi/v1/pay/transactions"), ErrorBinance);
  assertEquals(e.motivo, "red");
  assert(!e.message.includes("signature"));
  assert(!e.message.includes(CRED.apiKey));
});

Deno.test("clasifica 451, 418, 429 y -1021", () => {
  assertEquals(clasificarError(451, 0), "region");
  assertEquals(clasificarError(418, undefined), "bloqueo_ip");
  assertEquals(clasificarError(429, undefined), "limite");
  assertEquals(clasificarError(400, -1021), "reloj");
  assertEquals(clasificarError(400, -1100), "binance");
});

// ─── Normalización ───────────────────────────────────────────────────────────

const P2P_BASE = {
  orderNumber: "22654881234567890",
  tradeType: "BUY" as const,
  asset: "USDT",
  fiat: "VES",
  amount: "10.50000000",
  totalPrice: "5250.00",
  commission: "0",
  orderStatus: "COMPLETED",
  createTime: 1793750000000,
};

Deno.test("P2P completada: compra = entrada, guarda Bs y el JSON crudo", () => {
  const op = normalizarP2P(P2P_BASE)!;
  assertEquals(op.tipo, "p2p");
  assertEquals(op.direccion, "entrada");
  assertEquals(op.cantidad, "10.50000000");
  assertEquals(op.monto_fiat, "5250.00");
  assertEquals(op.fiat, "VES");
  assertEquals(op.id_binance, "22654881234567890");
  assertEquals(op.datos.orderNumber, P2P_BASE.orderNumber);
});

Deno.test("P2P venta = salida", () => {
  assertEquals(normalizarP2P({ ...P2P_BASE, tradeType: "SELL" })!.direccion, "salida");
});

for (const estado of ["PENDING", "TRADING", "BUYER_PAYED", "IN_APPEAL", "CANCELLED", "CANCELLED_BY_SYSTEM"]) {
  Deno.test(`P2P ${estado}: se ignora`, () => {
    assertEquals(normalizarP2P({ ...P2P_BASE, orderStatus: estado }), null);
  });
}

Deno.test("Pay: monto negativo = salida, cantidad sin signo", () => {
  const op = normalizarPay({ transactionId: "T1", transactionTime: 1793750000000, amount: "-3.25", currency: "USDT" });
  assertEquals(op.direccion, "salida");
  assertEquals(op.cantidad, "3.25");
  const rec = normalizarPay({ transactionId: "T2", transactionTime: 1793750000000, amount: "7", currency: "USDT" });
  assertEquals(rec.direccion, "entrada");
});

Deno.test("Depósito: solo status 1 (acreditado)", () => {
  const d = { id: "D1", amount: "20", coin: "USDT", status: 1, insertTime: 1793750000000 };
  assertEquals(normalizarDeposito(d)!.direccion, "entrada");
  for (const s of [0, 6, 7, 8, 2]) assertEquals(normalizarDeposito({ ...d, status: s }), null);
});

Deno.test("Retiro: solo status 6 (completado), con comisión y fecha UTC", () => {
  const r = { id: "W1", amount: "15", transactionFee: "1", coin: "USDT", status: 6, applyTime: "2026-10-12 11:12:02" };
  const op = normalizarRetiro(r)!;
  assertEquals(op.direccion, "salida");
  assertEquals(op.comision, "1");
  assertEquals(op.fecha, "2026-10-12T11:12:02.000Z");
  for (const s of [0, 1, 2, 3, 4, 5]) assertEquals(normalizarRetiro({ ...r, status: s }), null);
});

Deno.test("montos no numéricos o fechas raras se rechazan (no se adivinan)", () => {
  assertThrows(() => decimal("1e5", "x"));
  assertThrows(() => decimal("", "x"));
  assertThrows(() => decimal("abc", "x"));
  assertThrows(() => normalizarP2P({ ...P2P_BASE, amount: "NaN" }));
  assertThrows(() => normalizarP2P({ ...P2P_BASE, createTime: 0 }));
  assertThrows(() => fechaTextoUtc("12/10/2026", "x"));
  assertThrows(() => normalizarP2P({ ...P2P_BASE, tradeType: "OTRO" as "BUY" }));
});

Deno.test("ventanas cubren el rango sin huecos ni solapes", () => {
  const v = ventanas(0, 100, 30);
  assertEquals(v, [[0, 30], [30, 60], [60, 90], [90, 100]]);
  assertEquals(ventanas(5, 5, 30), []);
  assertThrows(() => ventanas(0, 10, 0));
});
