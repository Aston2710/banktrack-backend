// ─── Cálculo de comisiones bancarias ──────────────────────────────────────────
// Traducción fiel de comisiones.py

import type { Comision, DatosParseo } from "./types.ts";

/**
 * Regla BVC pagomóvil:
 * - 0.3% del monto
 * - Mínimo 2 Bs
 */
export function calcularComisionPagomovil(montoBs: number): number {
  const comision = Math.round(montoBs * 0.003 * 100) / 100;
  return Math.max(comision, 2.0);
}

/**
 * Retorna {monto, fuente}
 * - transferencia → monto declarado por el banco, fuente "declarada"
 * - enviado / pago_inmediato → calcula 0.3% con mínimo 2 Bs, fuente "calculada"
 *   (ambos son pago móvil sin comisión declarada en el correo)
 * - servicio → 0.0, fuente "exonerada" (regulación BCV)
 * - rechazado/entradas/otros → 0.0 o tarifa plana, fuente null
 */
export function resolverComision(transaccion: DatosParseo): Comision {
  const subtipo = transaccion.subtipo;
  const monto = transaccion.monto_bs ?? 0.0;

  if (subtipo === "transferencia") {
    const montoCom = transaccion.comision_declarada_bs ?? 0.0;
    return { monto: montoCom, fuente: "declarada" };
  } else if (subtipo === "enviado" || subtipo === "pago_inmediato") {
    return { monto: calcularComisionPagomovil(monto), fuente: "calculada" };
  } else if (subtipo === "rechazado") {
    return { monto: 2.0, fuente: null };
  } else if (subtipo === "servicio") {
    return { monto: 0.0, fuente: "exonerada" };
  } else {
    return { monto: 0.0, fuente: null };
  }
}
