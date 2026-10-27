// ─── Cliente Supabase y operaciones sobre transacciones ───────────────────────
// Traducción fiel de supabase_client.py

import { createClient, SupabaseClient } from "@supabase/supabase-js";

// ─── Columnas opcionales (pueden no existir en la BD) ────────────────────────
const COLUMNAS_OPCIONALES = ["tasa_euro", "monto_eur"];

// ─── Singleton del cliente ───────────────────────────────────────────────────

let _cliente: SupabaseClient | null = null;

// La clave es SB_SECRET_KEY (la secret key «db_vol» del panel). Si falta, se
// usa la «default» de SUPABASE_SECRET_KEYS, que la plataforma inyecta sola en
// las Edge Functions como JSON { nombre: "sb_secret_..." }. Se dejó de usar la
// service_role legacy (SB_SERVICE_ROLE_KEY) porque estuvo expuesta en el
// incidente de Railway de octubre 2026 y las legacy se desactivaron.
function claveSecreta(): string {
  const propia = Deno.env.get("SB_SECRET_KEY");
  if (propia) return propia;
  try {
    const claves = JSON.parse(Deno.env.get("SUPABASE_SECRET_KEYS") ?? "{}") as Record<string, string>;
    return claves.default ?? Object.values(claves)[0] ?? "";
  } catch {
    return "";
  }
}

export function getClient(): SupabaseClient {
  if (_cliente) return _cliente;
  const url = Deno.env.get("SB_URL") ?? "";
  const key = claveSecreta();
  if (!key) throw new Error("[supabase] SUPABASE_SECRET_KEYS no trae ninguna clave");
  _cliente = createClient(url, key);
  return _cliente;
}

// ─── Helpers internos ────────────────────────────────────────────────────────

function _soloDigitos(valor: string | null | undefined): string {
  return (valor ?? "").replace(/\D/g, "");
}

function _esEnmascarado(valor: string | null | undefined): boolean {
  return !!valor && valor.includes("*");
}

function _mismosUltimos2(a: string | null | undefined, b: string | null | undefined): boolean {
  const da = _soloDigitos(a);
  const db = _soloDigitos(b);
  return da.length >= 2 && db.length >= 2 && da.slice(-2) === db.slice(-2);
}

/** Valor legible para el log; '—' si está vacío. */
function _fmt(valor: unknown): string {
  return valor == null || valor === "" ? "—" : String(valor);
}

/** Resumen consistente con los valores clave de una transacción. */
function _resumen(datos: Record<string, unknown>): string {
  const partes = [
    `Bs. ${_fmt(datos.monto_bs)}`,
    `USD ${_fmt(datos.monto_usd)}`,
    `EUR ${_fmt(datos.monto_eur)}`,
    `concepto: ${_fmt(datos.concepto)}`,
  ];
  return partes.join(" | ");
}

function _esErrorColumnaFaltante(mensaje: string): boolean {
  const m = mensaje.toLowerCase();
  return m.includes("pgrst204") || (m.includes("column") && (m.includes("does not exist") || m.includes("could not find")));
}

// ─── Insertar transacción ────────────────────────────────────────────────────

export async function insertarTransaccion(
  client: SupabaseClient,
  datos: Record<string, unknown>
): Promise<boolean> {
  try {
    const { error } = await client.from("transacciones").insert(datos);
    if (error) throw error;

    console.log(
      `[supabase] ✅ Insertada: ${datos.subtipo} | ref: ${datos.referencia} | ${_resumen(datos)}`
    );
    return true;
  } catch (e: unknown) {
    const mensaje = String(e && typeof e === "object" && "message" in e ? (e as { message: string }).message : e);

    if (mensaje.toLowerCase().includes("duplicate") || mensaje.toLowerCase().includes("unique")) {
      console.log(`[supabase] ⚠️  Ya existe email_id: ${datos.email_id} — ignorado`);
      return false;
    }

    if (_esErrorColumnaFaltante(mensaje)) {
      const reducido: Record<string, unknown> = {};
      for (const [k, v] of Object.entries(datos)) {
        if (!COLUMNAS_OPCIONALES.includes(k)) reducido[k] = v;
      }
      console.log(
        "[supabase] ⚠️  Columnas EUR no existen en la BD — reintentando sin ellas. " +
        "Ejecuta el SQL de md/base-de-datos.md para habilitarlas."
      );
      try {
        const { error: e2 } = await client.from("transacciones").insert(reducido);
        if (e2) throw e2;
        console.log(
          `[supabase] ✅ Insertada (sin EUR): ref: ${datos.referencia} | ${_resumen(reducido)}`
        );
        return true;
      } catch (e2) {
        console.log(`[supabase] ❌ Error insertando (reintento): ${e2}`);
        return false;
      }
    }

    console.log(`[supabase] ❌ Error insertando: ${e}`);
    return false;
  }
}

// ─── Verificar referencia existente ──────────────────────────────────────────

export async function existeReferencia(
  client: SupabaseClient,
  referencia: string | null
): Promise<boolean> {
  if (!referencia) return false;
  try {
    const { data, error } = await client
      .from("transacciones")
      .select("id")
      .eq("referencia", referencia);
    if (error) throw error;
    return (data?.length ?? 0) > 0;
  } catch (e) {
    console.log(`[supabase] Error verificando referencia: ${e}`);
    return false;
  }
}

// ─── Obtener por referencia (interno) ────────────────────────────────────────

async function _obtenerPorReferencia(
  client: SupabaseClient,
  referencia: string
): Promise<Record<string, unknown> | null> {
  try {
    const { data, error } = await client
      .from("transacciones")
      .select("*")
      .eq("referencia", referencia)
      .limit(1);
    if (error) throw error;
    return data && data.length > 0 ? data[0] : null;
  } catch (e) {
    console.log(`[supabase] Error obteniendo por referencia: ${e}`);
    return null;
  }
}

// ─── Enriquecer transacción ──────────────────────────────────────────────────

export async function enriquecerTransaccion(
  client: SupabaseClient,
  referencia: string,
  datosNuevos: Record<string, unknown>
): Promise<boolean> {
  const existente = await _obtenerPorReferencia(client, referencia);
  if (!existente) return false;

  const camposAActualizar: Record<string, unknown> = {};

  // Campos candidatos a enriquecimiento
  const candidatos = [
    "concepto",
    "fecha",
    "contacto_destino",
    "banco_destino",
    "comercio",
    "tarjeta_ultimos",
    "etiquetas",
    "celular_origen",
    "beneficiario",
    "monto_bs",
    "tasa_dolar",
    "monto_usd",
    "tasa_euro",
    "monto_eur",
  ];

  for (const campo of candidatos) {
    const valorNuevo = datosNuevos[campo];
    const valorExistente = existente[campo];

    // Solo actualizar si el nuevo tiene valor y el existente está vacío
    if (valorNuevo && !valorExistente) {
      camposAActualizar[campo] = valorNuevo;
    }
  }

  // contacto_destino: si el registro existente tiene el número ENMASCARADO
  // y el correo nuevo trae el número COMPLETO, lo mejoramos — pero solo si
  // coinciden los últimos 2 dígitos.
  const nuevoContacto = datosNuevos.contacto_destino as string | null;
  const contactoExistente = existente.contacto_destino as string | null;
  if (
    nuevoContacto &&
    _esEnmascarado(contactoExistente) &&
    !_esEnmascarado(nuevoContacto) &&
    _mismosUltimos2(nuevoContacto, contactoExistente)
  ) {
    camposAActualizar.contacto_destino = nuevoContacto;
  }

  if (Object.keys(camposAActualizar).length === 0) {
    console.log(
      `[supabase] ⏭️  Duplicado sin datos nuevos: ref ${referencia} — ignorado | ${_resumen(existente as Record<string, unknown>)}`
    );
    return false;
  }

  try {
    const { error } = await client
      .from("transacciones")
      .update(camposAActualizar)
      .eq("referencia", referencia);
    if (error) throw error;

    const cambiosStr = Object.entries(camposAActualizar)
      .map(([campo, valor]) => `${campo}: ${_fmt(existente[campo])} → ${_fmt(valor)}`)
      .join(", ");
    console.log(`[supabase] 🔄 Enriquecida ref ${referencia}: ${cambiosStr}`);
    return true;
  } catch (e: unknown) {
    const mensaje = String(e && typeof e === "object" && "message" in e ? (e as { message: string }).message : e);

    if (_esErrorColumnaFaltante(mensaje)) {
      const reducido: Record<string, unknown> = {};
      for (const [k, v] of Object.entries(camposAActualizar)) {
        if (!COLUMNAS_OPCIONALES.includes(k)) reducido[k] = v;
      }
      if (Object.keys(reducido).length === 0) {
        console.log(
          `[supabase] ⏭️  Solo había columnas EUR (inexistentes) para enriquecer ref ${referencia} — ignorado`
        );
        return false;
      }
      console.log(
        "[supabase] ⚠️  Columnas EUR no existen en la BD — enriqueciendo sin ellas. " +
        "Ejecuta el SQL de md/base-de-datos.md para habilitarlas."
      );
      try {
        const { error: e2 } = await client
          .from("transacciones")
          .update(reducido)
          .eq("referencia", referencia);
        if (e2) throw e2;

        const cambiosStr = Object.entries(reducido)
          .map(([campo, valor]) => `${campo}: ${_fmt(existente[campo])} → ${_fmt(valor)}`)
          .join(", ");
        console.log(`[supabase] 🔄 Enriquecida (sin EUR) ref ${referencia}: ${cambiosStr}`);
        return true;
      } catch (e2) {
        console.log(`[supabase] Error enriqueciendo (reintento): ${e2}`);
        return false;
      }
    }

    console.log(`[supabase] Error enriqueciendo: ${e}`);
    return false;
  }
}

// ─── Consultas de lectura ────────────────────────────────────────────────────

export async function obtenerTransaccionesMes(
  client: SupabaseClient,
  mes: string
): Promise<Record<string, unknown>[]> {
  try {
    const { data, error } = await client
      .from("transacciones")
      .select("*")
      .eq("mes_corte", mes)
      .order("fecha", { ascending: false });
    if (error) throw error;
    return data ?? [];
  } catch (e) {
    console.log(`[supabase] Error consultando mes ${mes}: ${e}`);
    return [];
  }
}

export async function obtenerConfiguracion(
  client: SupabaseClient
): Promise<Record<string, unknown>> {
  try {
    const { data, error } = await client
      .from("configuracion")
      .select("*")
      .limit(1);
    if (error) throw error;
    return data && data.length > 0 ? data[0] : {};
  } catch (e) {
    console.log(`[supabase] Error obteniendo configuración: ${e}`);
    return {};
  }
}

export async function guardarCierreMensual(
  client: SupabaseClient,
  mes: string
): Promise<boolean> {
  try {
    const transacciones = await obtenerTransaccionesMes(client, mes);
    if (transacciones.length === 0) {
      console.log(`[supabase] Sin transacciones para cerrar mes ${mes}`);
      return false;
    }

    const entradasBs = transacciones
      .filter((t) => t.tipo === "entrada")
      .reduce((s, t) => s + ((t.monto_bs as number) ?? 0), 0);
    const salidasBs = transacciones
      .filter((t) => t.tipo === "salida")
      .reduce((s, t) => s + ((t.monto_bs as number) ?? 0), 0);
    const entradasUsd = transacciones
      .filter((t) => t.tipo === "entrada")
      .reduce((s, t) => s + ((t.monto_usd as number) ?? 0), 0);
    const salidasUsd = transacciones
      .filter((t) => t.tipo === "salida")
      .reduce((s, t) => s + ((t.monto_usd as number) ?? 0), 0);
    const entradasEur = transacciones
      .filter((t) => t.tipo === "entrada")
      .reduce((s, t) => s + ((t.monto_eur as number) ?? 0), 0);
    const salidasEur = transacciones
      .filter((t) => t.tipo === "salida")
      .reduce((s, t) => s + ((t.monto_eur as number) ?? 0), 0);
    const comisiones = transacciones.reduce(
      (s, t) => s + ((t.comision_bs as number) ?? 0),
      0
    );

    const tasas = transacciones
      .filter((t) => t.tasa_dolar)
      .map((t) => t.tasa_dolar as number);
    const tasaProm = tasas.length > 0
      ? Math.round((tasas.reduce((a, b) => a + b, 0) / tasas.length) * 10000) / 10000
      : null;

    const tasasEur = transacciones
      .filter((t) => t.tasa_euro)
      .map((t) => t.tasa_euro as number);
    const tasaPromEur = tasasEur.length > 0
      ? Math.round((tasasEur.reduce((a, b) => a + b, 0) / tasasEur.length) * 10000) / 10000
      : null;

    const pctComision = salidasBs > 0
      ? Math.round((comisiones / salidasBs * 100) * 10000) / 10000
      : 0;

    const cierre: Record<string, unknown> = {
      mes,
      total_entradas_bs:     Math.round(entradasBs * 100) / 100,
      total_salidas_bs:      Math.round(salidasBs * 100) / 100,
      total_entradas_usd:    Math.round(entradasUsd * 10000) / 10000,
      total_salidas_usd:     Math.round(salidasUsd * 10000) / 10000,
      total_entradas_eur:    Math.round(entradasEur * 10000) / 10000,
      total_salidas_eur:     Math.round(salidasEur * 10000) / 10000,
      total_comisiones_bs:   Math.round(comisiones * 100) / 100,
      porcentaje_comisiones: pctComision,
      tasa_promedio_mes:     tasaProm,
      tasa_promedio_eur_mes: tasaPromEur,
      cerrado_en:            new Date().toISOString(),
    };

    try {
      const { error } = await client.from("cierres_mensuales").upsert(cierre);
      if (error) throw error;
    } catch (e: unknown) {
      const msg = String(e && typeof e === "object" && "message" in e ? (e as { message: string }).message : e);
      if (!_esErrorColumnaFaltante(msg)) throw e;

      const reducido: Record<string, unknown> = {};
      for (const [k, v] of Object.entries(cierre)) {
        if (!["total_entradas_eur", "total_salidas_eur", "tasa_promedio_eur_mes"].includes(k)) {
          reducido[k] = v;
        }
      }
      console.log(
        "[supabase] ⚠️  Columnas EUR no existen en cierres_mensuales — guardando sin ellas. " +
        "Ejecuta el SQL de md/base-de-datos.md."
      );
      const { error: e2 } = await client.from("cierres_mensuales").upsert(reducido);
      if (e2) throw e2;
    }

    console.log(`[supabase] Cierre mensual guardado: ${mes}`);
    return true;
  } catch (e) {
    console.log(`[supabase] Error guardando cierre: ${e}`);
    return false;
  }
}
