// ─── Edge Function: API REST ──────────────────────────────────────────────────
// Traducción fiel de api.py (FastAPI → Hono)
// Mismos endpoints, mismas restricciones de campos, mismos cálculos.

import { Hono } from "hono";
import { cors } from "hono/cors";
import {
  getClient,
  obtenerTransaccionesMes,
  obtenerConfiguracion,
} from "../_shared/supabase-client.ts";

// Supabase monta la funcion en /api, asi que las rutas cuelgan de ese prefijo.
const app = new Hono().basePath("/api");

const API_KEY = Deno.env.get("API_KEY") ?? "";

// ── CORS ─────────────────────────────────────────────────────────────────────
app.use(
  "*",
  cors({
    origin: "*",
    allowMethods: ["GET", "PATCH"],
    allowHeaders: ["Authorization", "Content-Type"],
  })
);

// ── Middleware de autenticación Bearer ────────────────────────────────────────
app.use("*", async (c, next) => {
  // Rutas públicas: raíz y health
  const path = new URL(c.req.url).pathname;
  // Normalizar: quitar prefijo /api si existe (Supabase monta la función en /api)
  const ruta = path.replace(/^\/api/, "") || "/";
  if (ruta === "/" || ruta === "/health") {
    return next();
  }

  const auth = c.req.header("Authorization") ?? "";
  const token = auth.replace(/^Bearer\s+/i, "");
  if (token !== API_KEY) {
    return c.json({ detail: "No autorizado" }, 401);
  }
  return next();
});

// ── Raíz y health check ──────────────────────────────────────────────────────
app.get("/", (c) => c.redirect("/api/health"));
app.get("/health", (c) =>
  c.json({ status: "ok", timestamp: new Date().toISOString() })
);

// ── Transacciones ────────────────────────────────────────────────────────────

/** Retorna todas las transacciones de un mes. Formato: 2026-06 */
app.get("/transacciones/:mes", async (c) => {
  const mes = c.req.param("mes");
  const client = getClient();
  const data = await obtenerTransaccionesMes(client, mes);
  return c.json(data);
});

/** Filtra transacciones por subtipo: enviado, recibido, tarjeta, etc. */
app.get("/transacciones/:mes/subtipo/:subtipo", async (c) => {
  const mes = c.req.param("mes");
  const subtipo = c.req.param("subtipo");
  const client = getClient();
  const todas = await obtenerTransaccionesMes(client, mes);
  const filtradas = todas.filter((t) => t.subtipo === subtipo);
  return c.json(filtradas);
});

/**
 * Permite editar campos no sensibles: categoria, nota, etiquetas.
 * El monto nunca se puede modificar.
 */
app.patch("/transacciones/:id", async (c) => {
  const id = c.req.param("id");
  const body = await c.req.json();

  const camposEditables = new Set(["categoria", "nota", "etiquetas"]);
  const camposRecibidos = Object.keys(body);
  const camposNoPermitidos = camposRecibidos.filter((k) => !camposEditables.has(k));

  if (camposNoPermitidos.length > 0) {
    return c.json(
      { detail: `Campos no editables: ${camposNoPermitidos.join(", ")}` },
      400
    );
  }

  try {
    const client = getClient();
    const { error } = await client
      .from("transacciones")
      .update(body)
      .eq("id", id);
    if (error) throw error;
    return c.json({ ok: true, id, actualizado: body });
  } catch (e) {
    return c.json({ detail: String(e) }, 500);
  }
});

// ── Resumen mensual ──────────────────────────────────────────────────────────

/** Totales del mes: entradas, salidas, comisiones, balance. */
app.get("/resumen/:mes", async (c) => {
  const mes = c.req.param("mes");
  const client = getClient();
  const transacciones = await obtenerTransaccionesMes(client, mes);

  const entradas = transacciones
    .filter((t) => t.tipo === "entrada")
    .reduce((s, t) => s + ((t.monto_bs as number) ?? 0), 0);
  const salidas = transacciones
    .filter((t) => t.tipo === "salida")
    .reduce((s, t) => s + ((t.monto_bs as number) ?? 0), 0);
  const comisiones = transacciones.reduce(
    (s, t) => s + ((t.comision_bs as number) ?? 0),
    0
  );
  const tasas = transacciones
    .filter((t) => t.tasa_dolar)
    .map((t) => t.tasa_dolar as number);
  const tasaProm =
    tasas.length > 0
      ? Math.round((tasas.reduce((a, b) => a + b, 0) / tasas.length) * 10000) / 10000
      : null;

  const tasasEur = transacciones
    .filter((t) => t.tasa_euro)
    .map((t) => t.tasa_euro as number);
  const tasaPromEur =
    tasasEur.length > 0
      ? Math.round((tasasEur.reduce((a, b) => a + b, 0) / tasasEur.length) * 10000) / 10000
      : null;

  return c.json({
    mes,
    entradas_bs:       Math.round(entradas * 100) / 100,
    salidas_bs:        Math.round(salidas * 100) / 100,
    balance_bs:        Math.round((entradas - salidas) * 100) / 100,
    comisiones_bs:     Math.round(comisiones * 100) / 100,
    pct_comisiones:    salidas > 0 ? Math.round((comisiones / salidas * 100) * 100) / 100 : 0,
    entradas_usd:      tasaProm ? Math.round((entradas / tasaProm) * 100) / 100 : null,
    salidas_usd:       tasaProm ? Math.round((salidas / tasaProm) * 100) / 100 : null,
    balance_usd:       tasaProm ? Math.round(((entradas - salidas) / tasaProm) * 100) / 100 : null,
    entradas_eur:      tasaPromEur ? Math.round((entradas / tasaPromEur) * 100) / 100 : null,
    salidas_eur:       tasaPromEur ? Math.round((salidas / tasaPromEur) * 100) / 100 : null,
    balance_eur:       tasaPromEur ? Math.round(((entradas - salidas) / tasaPromEur) * 100) / 100 : null,
    tasa_promedio:     tasaProm,
    tasa_promedio_eur: tasaPromEur,
    total_movimientos: transacciones.length,
  });
});

// ── Estadísticas ─────────────────────────────────────────────────────────────

/** Desglose de gastos por subtipo para gráficas. */
app.get("/estadisticas/:mes", async (c) => {
  const mes = c.req.param("mes");
  const client = getClient();
  const transacciones = await obtenerTransaccionesMes(client, mes);

  const subtipos: Record<string, number> = {};
  for (const t of transacciones) {
    if (t.tipo === "salida" || t.tipo === "rechazado") {
      const s = (t.subtipo as string) ?? "desconocido";
      subtipos[s] = (subtipos[s] ?? 0) + ((t.monto_bs as number) ?? 0);
    }
  }

  const porSubtipo = Object.entries(subtipos)
    .sort((a, b) => b[1] - a[1])
    .map(([subtipo, total]) => ({
      subtipo,
      total_bs: Math.round(total * 100) / 100,
    }));

  return c.json({ mes, por_subtipo: porSubtipo });
});

// ── Configuración ────────────────────────────────────────────────────────────

app.get("/configuracion", async (c) => {
  const client = getClient();
  const config = await obtenerConfiguracion(client);
  return c.json(config);
});

app.patch("/configuracion/:id", async (c) => {
  const id = c.req.param("id");
  const body = await c.req.json();

  const camposEditables = new Set([
    "limite_mensual_bs",
    "limite_mensual_usd",
    "alerta_porcentaje",
    "moneda_principal",
  ]);
  const camposNoPermitidos = Object.keys(body).filter(
    (k) => !camposEditables.has(k)
  );

  if (camposNoPermitidos.length > 0) {
    return c.json(
      { detail: `Campos no editables: ${camposNoPermitidos.join(", ")}` },
      400
    );
  }

  try {
    const client = getClient();
    const { error } = await client
      .from("configuracion")
      .update(body)
      .eq("id", id);
    if (error) throw error;
    return c.json({ ok: true, actualizado: body });
  } catch (e) {
    return c.json({ detail: String(e) }, 500);
  }
});

// ── Cierres mensuales ────────────────────────────────────────────────────────

app.get("/cierres", async (c) => {
  try {
    const client = getClient();
    const { data, error } = await client
      .from("cierres_mensuales")
      .select("*")
      .order("mes", { ascending: false });
    if (error) throw error;
    return c.json(data ?? []);
  } catch (e) {
    return c.json({ detail: String(e) }, 500);
  }
});

// ── Iniciar servidor ─────────────────────────────────────────────────────────
Deno.serve(app.fetch);
