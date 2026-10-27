// ─── Lector de correos Gmail via REST API ─────────────────────────────────────
// Traducción fiel de gmail_reader.py — adaptada para Deno/Edge Functions.
// Token almacenado en tabla `gmail_tokens` (single row id=1).

import type { SupabaseClient } from "@supabase/supabase-js";
import type { Correo } from "./types.ts";

const GOOGLE_CLIENT_ID     = Deno.env.get("GOOGLE_CLIENT_ID") ?? "";
const GOOGLE_CLIENT_SECRET = Deno.env.get("GOOGLE_CLIENT_SECRET") ?? "";
const GMAIL_LABEL          = Deno.env.get("GMAIL_LABEL") ?? "BVC";

// ─── Gestión de token OAuth2 ─────────────────────────────────────────────────

interface GmailToken {
  access_token: string;
  refresh_token: string;
  expiry: string; // ISO timestamp
}

/**
 * Lee el token de gmail_tokens (id=1), lo refresca si expiró,
 * y guarda el nuevo token de vuelta.
 */
export async function getValidToken(supabase: SupabaseClient): Promise<string> {
  const { data, error } = await supabase
    .from("gmail_tokens")
    .select("*")
    .eq("id", 1)
    .single();

  if (error || !data) {
    throw new Error(`[gmail] No se pudo leer token de gmail_tokens: ${error?.message}`);
  }

  const token = data as GmailToken & { id: number };
  const ahora = new Date();
  const expiry = new Date(token.expiry);

  // Si el token aún es válido (con 60s de margen), retornarlo
  if (expiry.getTime() - ahora.getTime() > 60_000) {
    return token.access_token;
  }

  // Refrescar el token
  console.log("[gmail] Token expirado — refrescando...");
  const resp = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      client_id: GOOGLE_CLIENT_ID,
      client_secret: GOOGLE_CLIENT_SECRET,
      refresh_token: token.refresh_token,
      grant_type: "refresh_token",
    }),
  });

  if (!resp.ok) {
    const body = await resp.text();
    throw new Error(`[gmail] Error refrescando token: ${resp.status} ${body}`);
  }

  const nuevo = await resp.json();
  const nuevoExpiry = new Date(ahora.getTime() + (nuevo.expires_in ?? 3600) * 1000);

  // Guardar token actualizado en la BD
  const { error: updateError } = await supabase
    .from("gmail_tokens")
    .update({
      access_token: nuevo.access_token,
      expiry: nuevoExpiry.toISOString(),
    })
    .eq("id", 1);

  if (updateError) {
    console.log(`[gmail] Advertencia: no se pudo guardar token actualizado: ${updateError.message}`);
  }

  console.log("[gmail] Token refrescado exitosamente");
  return nuevo.access_token;
}

// ─── Decodificación del cuerpo ───────────────────────────────────────────────

/**
 * Decodifica base64url a string UTF-8.
 * Reemplaza caracteres de base64url (-_ → +/) y agrega padding.
 */
function _b64Decode(data: string): string {
  const padded = data.replace(/-/g, "+").replace(/_/g, "/");
  const pad = padded.length % 4;
  const finalStr = pad ? padded + "=".repeat(4 - pad) : padded;
  const bytes = Uint8Array.from(atob(finalStr), (c) => c.charCodeAt(0));
  return new TextDecoder("utf-8").decode(bytes);
}

/** Extrae el texto plano del cuerpo del correo recursivamente. */
export function decodificarCuerpo(payload: Record<string, unknown>): string {
  let cuerpo = "";

  function extraerPartes(partes: Record<string, unknown>[]): string {
    let texto = "";
    for (const parte of partes) {
      const mime = (parte.mimeType as string) ?? "";
      if (mime === "text/plain") {
        const data = ((parte.body as Record<string, unknown>)?.data as string) ?? "";
        if (data) {
          texto += _b64Decode(data);
        }
      } else if (Array.isArray(parte.parts)) {
        texto += extraerPartes(parte.parts as Record<string, unknown>[]);
      }
    }
    return texto;
  }

  if (Array.isArray(payload.parts)) {
    cuerpo = extraerPartes(payload.parts as Record<string, unknown>[]);
  } else {
    const data = ((payload.body as Record<string, unknown>)?.data as string) ?? "";
    if (data) {
      cuerpo = _b64Decode(data);
    }
  }

  return cuerpo;
}

// ─── Obtener correos no leídos ───────────────────────────────────────────────

export async function obtenerCorreosNoLeidos(supabase: SupabaseClient): Promise<Correo[]> {
  const accessToken = await getValidToken(supabase);
  const correos: Correo[] = [];

  try {
    // Buscar hilos con la etiqueta BVC no leídos
    const listUrl =
      `https://gmail.googleapis.com/gmail/v1/users/me/threads?labelIds=${GMAIL_LABEL}&q=is:unread`;
    const listResp = await fetch(listUrl, {
      headers: { Authorization: `Bearer ${accessToken}` },
    });

    if (!listResp.ok) {
      throw new Error(`HTTP ${listResp.status}: ${await listResp.text()}`);
    }

    const listData = await listResp.json();
    const hilos = (listData.threads ?? []) as { id: string }[];
    console.log(`[gmail] Hilos no leídos encontrados: ${hilos.length}`);

    for (const hilo of hilos) {
      // Obtener todos los mensajes del hilo
      const threadUrl =
        `https://gmail.googleapis.com/gmail/v1/users/me/threads/${hilo.id}?format=full`;
      const threadResp = await fetch(threadUrl, {
        headers: { Authorization: `Bearer ${accessToken}` },
      });

      if (!threadResp.ok) continue;

      const threadData = await threadResp.json();
      const mensajes = (threadData.messages ?? []) as Record<string, unknown>[];

      for (const mensaje of mensajes) {
        // Solo procesar mensajes no leídos
        const etiquetas = (mensaje.labelIds as string[]) ?? [];
        if (!etiquetas.includes("UNREAD")) continue;

        const headers = ((mensaje.payload as Record<string, unknown>)?.headers ?? []) as {
          name: string;
          value: string;
        }[];
        const asunto = headers.find((h) => h.name === "Subject")?.value ?? "";
        const cuerpo = decodificarCuerpo(
          (mensaje.payload as Record<string, unknown>) ?? {}
        );

        correos.push({
          id: mensaje.id as string,
          asunto,
          cuerpo,
        });
      }
    }

    console.log(`[gmail] Mensajes no leídos totales: ${correos.length}`);
  } catch (e) {
    console.log(`[gmail] Error obteniendo correos: ${e}`);
  }

  return correos;
}

// ─── Marcar como leído ───────────────────────────────────────────────────────

export async function marcarComoLeido(
  supabase: SupabaseClient,
  emailId: string
): Promise<void> {
  const accessToken = await getValidToken(supabase);
  try {
    const url = `https://gmail.googleapis.com/gmail/v1/users/me/messages/${emailId}/modify`;
    const resp = await fetch(url, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${accessToken}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ removeLabelIds: ["UNREAD"] }),
    });

    if (resp.ok) {
      console.log(`[gmail] Marcado como leído: ${emailId}`);
    } else {
      console.log(`[gmail] Error marcando como leído ${emailId}: ${resp.status}`);
    }
  } catch (e) {
    console.log(`[gmail] Error marcando como leído ${emailId}: ${e}`);
  }
}
