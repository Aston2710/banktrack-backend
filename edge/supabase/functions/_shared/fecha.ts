// ─── Utilidades de fecha en horario de Venezuela ──────────────────────────────
// El Edge Runtime corre en UTC, no en la zona horaria local como el backend
// Python. Venezuela usa UTC-4 fijo (sin horario de verano desde 2016), así que
// el desfase se aplica de forma explícita en vez de depender del sistema.

const VE_OFFSET_MS = 4 * 60 * 60 * 1000;

/**
 * Construye el instante real a partir de una hora de pared venezolana.
 * Ej: 12/09/2026 21:30 VE → 2026-09-13T01:30:00Z
 */
export function desdeHoraVE(
  anio: number,
  mesIndice: number,
  dia: number,
  hora: number,
  minuto: number,
  segundo: number
): Date {
  return new Date(Date.UTC(anio, mesIndice, dia, hora, minuto, segundo) + VE_OFFSET_MS);
}

/** Partes del calendario venezolano de un instante dado. */
function _partesVE(fecha: Date): { anio: number; mes: number; dia: number } {
  const desplazada = new Date(fecha.getTime() - VE_OFFSET_MS);
  return {
    anio: desplazada.getUTCFullYear(),
    mes: desplazada.getUTCMonth() + 1,
    dia: desplazada.getUTCDate(),
  };
}

/** 'YYYY-MM' según el calendario venezolano. */
export function mesVE(fecha: Date): string {
  const { anio, mes } = _partesVE(fecha);
  return `${anio}-${String(mes).padStart(2, "0")}`;
}

/** 'YYYY-MM-DD' según el calendario venezolano. */
export function fechaVE(fecha: Date): string {
  const { anio, mes, dia } = _partesVE(fecha);
  return `${anio}-${String(mes).padStart(2, "0")}-${String(dia).padStart(2, "0")}`;
}

/** true si ambos instantes caen el mismo día en Venezuela. */
export function mismoDiaVE(a: Date, b: Date): boolean {
  return fechaVE(a) === fechaVE(b);
}
