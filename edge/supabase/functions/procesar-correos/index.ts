// ─── Edge Function: procesar-correos ──────────────────────────────────────────
// Traducción fiel de main.py procesar_correos() — misma lógica, mismo flujo.
// Una sola función que se invoca por cron o HTTP POST.

import { getClient, insertarTransaccion, existeReferencia, enriquecerTransaccion } from "../_shared/supabase-client.ts";
import { obtenerCorreosNoLeidos, marcarComoLeido } from "../_shared/gmail.ts";
import { parsearCorreo } from "../_shared/parser.ts";
import { resolverComision } from "../_shared/comisiones.ts";
import { obtenerTasaBcv, obtenerTasaEuro } from "../_shared/tasas.ts";
import { verificarLimiteMesActual } from "../_shared/alertas.ts";
import { mesVE, fechaVE, mismoDiaVE } from "../_shared/fecha.ts";
import type { Registro } from "../_shared/types.ts";

// ─── Autorización del cron ───────────────────────────────────────────────────
// pg_cron manda "Bearer <edge_invoke_key>" (Vault). Esa clave es CRON_KEY, un
// valor aleatorio que solo sirve para invocar esta función: no da acceso a la
// base. Reemplaza a la service_role legacy, que no se puede usar con
// verify_jwt porque las claves sb_secret_ no son JWT.
const CRON_KEY = Deno.env.get("CRON_KEY") ?? "";

function autorizado(req: Request): boolean {
  const recibido = (req.headers.get("Authorization") ?? "").replace(/^Bearer\s+/i, "");
  if (!CRON_KEY || recibido.length !== CRON_KEY.length) return false;
  // Comparación en tiempo constante.
  let diferencia = 0;
  for (let i = 0; i < CRON_KEY.length; i++) {
    diferencia |= recibido.charCodeAt(i) ^ CRON_KEY.charCodeAt(i);
  }
  return diferencia === 0;
}

Deno.serve(async (req) => {
  if (!autorizado(req)) {
    return new Response(JSON.stringify({ ok: false, error: "no autorizado" }), {
      status: 401,
      headers: { "Content-Type": "application/json" },
    });
  }

  const ahora = new Date();
  console.log(
    `\n[main] ─── Ciclo: ${ahora.toLocaleString("es-VE", { timeZone: "America/Caracas" })} ───`
  );

  const client = getClient();

  // ── Obtener tasas ───────────────────────────────────────────────────────────
  const tasa = await obtenerTasaBcv();
  if (tasa) {
    console.log(`[main] Tasa BCV: Bs. ${tasa}`);
  } else {
    console.log("[main] Sin tasa disponible — se guardará sin conversión USD");
  }

  const tasaEuro = await obtenerTasaEuro();
  if (tasaEuro) {
    console.log(`[main] Tasa EUR: Bs. ${tasaEuro}`);
  } else {
    console.log("[main] Sin tasa euro disponible — se guardará sin conversión EUR");
  }

  // ── Obtener correos ─────────────────────────────────────────────────────────
  const correos = await obtenerCorreosNoLeidos(client);
  if (correos.length === 0) {
    console.log("[main] Sin correos nuevos");
    return new Response(
      JSON.stringify({ ok: true, procesados: 0, insertados: 0, enriquecidos: 0, ignorados: 0 }),
      { headers: { "Content-Type": "application/json" } }
    );
  }

  let insertados = 0;
  let enriquecidos = 0;
  let ignorados = 0;

  for (const correo of correos) {
    const datos = parsearCorreo(correo.asunto, correo.cuerpo);
    const subtipo = datos.subtipo;
    const referencia = datos.referencia;

    // ── Desconocido ─────────────────────────────────────────────────────────
    if (subtipo === "desconocido") {
      console.log(`[main] ❓ No reconocido: ${correo.asunto.substring(0, 60)}`);
      await marcarComoLeido(client, correo.id);
      ignorados++;
      continue;
    }

    // ── Calcular monto real ─────────────────────────────────────────────────
    let montoReal = datos.monto_bs;
    if (subtipo === "rechazado") {
      montoReal = 0.0;
    }

    // La tasa BCV se consulta AHORA, no en la fecha real del pago.
    // Si el correo es de un día distinto a hoy, la tasa de hoy NO corresponde.
    const fechaPago = datos.fecha;
    const hoy = new Date();
    const esTasaDelDia = fechaPago !== null && mismoDiaVE(fechaPago, hoy);

    const tasaAplicable = esTasaDelDia ? tasa : null;
    const tasaEuroAplicable = esTasaDelDia ? tasaEuro : null;

    if (fechaPago !== null && !esTasaDelDia) {
      const fechaStr = fechaVE(fechaPago);
      console.log(
        `[main] ⚠️  Correo de fecha pasada (${fechaStr}) — se guarda sin tasa (no hay tasa histórica disponible)`
      );
    }

    let montoUsd: number | null = null;
    if (tasaAplicable && montoReal && montoReal > 0) {
      montoUsd = Math.round((montoReal / tasaAplicable) * 10000) / 10000;
    }

    let montoEur: number | null = null;
    if (tasaEuroAplicable && montoReal && montoReal > 0) {
      montoEur = Math.round((montoReal / tasaEuroAplicable) * 10000) / 10000;
    }

    const mesCorte = mesVE(datos.fecha ?? ahora);

    // ── Calcular comisión ───────────────────────────────────────────────────
    const comision = resolverComision(datos);

    // ── Armar registro ──────────────────────────────────────────────────────
    const registro: Registro = {
      email_id:         correo.id,
      fecha:            datos.fecha ? datos.fecha.toISOString() : ahora.toISOString(),
      tipo:             datos.tipo,
      subtipo:          subtipo,
      monto_bs:         montoReal,
      tasa_dolar:       tasaAplicable,
      monto_usd:        montoUsd,
      tasa_euro:        tasaEuroAplicable,
      monto_eur:        montoEur,
      referencia:       referencia,
      celular_origen:   datos.celular_origen ?? null,
      contacto_destino: datos.contacto_destino ?? null,
      banco_destino:    datos.banco_destino ?? null,
      beneficiario:     datos.beneficiario ?? null,
      comercio:         datos.comercio ?? null,
      tarjeta_ultimos:  datos.tarjeta_ultimos ?? null,
      comision_bs:      comision.monto,
      comision_fuente:  comision.fuente,
      mes_corte:        mesCorte,
      concepto:         datos.concepto ?? null,
      etiquetas:        datos.etiquetas ?? [],
    };

    // ── Duplicado por referencia → enriquecer ───────────────────────────────
    if (referencia && await existeReferencia(client, referencia)) {
      if (await enriquecerTransaccion(client, referencia, registro as unknown as Record<string, unknown>)) {
        enriquecidos++;
      } else {
        ignorados++;
      }
      await marcarComoLeido(client, correo.id);
      continue;
    }

    if (await insertarTransaccion(client, registro as unknown as Record<string, unknown>)) {
      insertados++;
    }

    await marcarComoLeido(client, correo.id);
  }

  // ── Resumen del ciclo ───────────────────────────────────────────────────────
  console.log(`\n[main] ── Resumen del ciclo ──────────────────────────────`);
  console.log(`[main]   Procesados:   ${correos.length}`);
  console.log(`[main]   Insertados:   ${insertados}`);
  console.log(`[main]   Enriquecidos: ${enriquecidos}`);
  console.log(`[main]   Ignorados:    ${ignorados}`);
  console.log(`[main] ─────────────────────────────────────────────────────`);

  // ── Verificar alertas ───────────────────────────────────────────────────────
  await verificarLimiteMesActual(client);

  return new Response(
    JSON.stringify({
      ok: true,
      procesados:   correos.length,
      insertados,
      enriquecidos,
      ignorados,
    }),
    { headers: { "Content-Type": "application/json" } }
  );
});
