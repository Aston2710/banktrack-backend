// ─── Sistema de alertas de límite mensual ─────────────────────────────────────
// Traducción fiel de alertas.py

import type { SupabaseClient } from "@supabase/supabase-js";
import { obtenerTransaccionesMes, obtenerConfiguracion } from "./supabase-client.ts";
import { mesVE } from "./fecha.ts";

interface EstadoAlerta {
  mes: string;
  gastado_bs: number;
  limite_bs: number;
  porcentaje: number;
  alerta: boolean;
  superado: boolean;
  mensaje: string;
}

/**
 * Revisa si el gasto del mes actual se acerca o supera el límite.
 * Retorna un dict con el estado actual.
 */
export async function verificarLimiteMesActual(
  client: SupabaseClient
): Promise<EstadoAlerta> {
  const mesActual = mesVE(new Date());

  const config = await obtenerConfiguracion(client);
  const limiteBs = (config.limite_mensual_bs as number) ?? 0;
  const alertaPct = (config.alerta_porcentaje as number) ?? 80;

  if (!limiteBs || limiteBs <= 0) {
    return {
      mes: mesActual,
      gastado_bs: 0,
      limite_bs: 0,
      porcentaje: 0,
      alerta: false,
      superado: false,
      mensaje: "Sin límite configurado",
    };
  }

  const transacciones = await obtenerTransaccionesMes(client, mesActual);
  const salidas = transacciones
    .filter((t) => t.tipo === "salida")
    .reduce((sum, t) => sum + ((t.monto_bs as number) ?? 0), 0);
  const porcentaje = (salidas / limiteBs) * 100;

  const estado: EstadoAlerta = {
    mes: mesActual,
    gastado_bs: Math.round(salidas * 100) / 100,
    limite_bs: limiteBs,
    porcentaje: Math.round(porcentaje * 100) / 100,
    alerta: false,
    superado: false,
    mensaje: "",
  };

  if (porcentaje >= 100) {
    estado.superado = true;
    estado.alerta = true;
    estado.mensaje = `⚠️ Límite SUPERADO: gastaste Bs. ${salidas.toLocaleString("es-VE", { minimumFractionDigits: 2 })} de Bs. ${limiteBs.toLocaleString("es-VE", { minimumFractionDigits: 2 })}`;
  } else if (porcentaje >= alertaPct) {
    estado.alerta = true;
    estado.mensaje = `⚠️ Alerta: ${porcentaje.toFixed(1)}% del límite usado (Bs. ${salidas.toLocaleString("es-VE", { minimumFractionDigits: 2 })} de Bs. ${limiteBs.toLocaleString("es-VE", { minimumFractionDigits: 2 })})`;
  } else {
    estado.mensaje = `✅ Gasto normal: ${porcentaje.toFixed(1)}% del límite`;
  }

  console.log(`[alertas] ${estado.mensaje}`);
  return estado;
}
