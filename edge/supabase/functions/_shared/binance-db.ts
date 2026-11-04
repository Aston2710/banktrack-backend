// Cliente de Supabase para sincronizar-binance. Misma lógica de clave que
// supabase-client.ts, pero sin arrastrar el módulo de transacciones.

import { createClient, type SupabaseClient } from "@supabase/supabase-js";

let _cliente: SupabaseClient | null = null;

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
  const url = Deno.env.get("SB_URL") ?? Deno.env.get("SUPABASE_URL") ?? "";
  const key = claveSecreta();
  if (!url || !key) throw new Error("[supabase] falta la URL o la clave secreta");
  _cliente = createClient(url, key, { auth: { persistSession: false } });
  return _cliente;
}
