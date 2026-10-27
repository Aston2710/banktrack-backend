// ─── Parser de correos bancarios BVC ──────────────────────────────────────────
// Traducción fiel de parser.py — misma lógica, mismos regex, mismo flujo.

import type { DatosParseo } from "./types.ts";
import { desdeHoraVE } from "./fecha.ts";

// ─── Constantes de tipo ──────────────────────────────────────────────────────
const TIPO_RECIBIDO       = "recibido";
const TIPO_ENVIADO        = "enviado";
const TIPO_TRANSFERENCIA  = "transferencia";
const TIPO_PAGO_INMEDIATO = "pago_inmediato";
const TIPO_TARJETA        = "tarjeta";
const TIPO_SERVICIO       = "servicio";
const TIPO_DESCONOCIDO    = "desconocido";

// ─── Identificar tipo de correo ──────────────────────────────────────────────
export function identificarTipo(asunto: string, cuerpo: string): string {
  const asuntoLower = asunto.toLowerCase();
  const cuerpoLower = cuerpo.toLowerCase();

  if (cuerpoLower.includes("fue rechazado")) {
    return "rechazado";
  }
  if (
    asuntoLower.includes("notificación de uso de su tarjeta") ||
    asuntoLower.includes("notificacion de uso de su tarjeta")
  ) {
    return TIPO_TARJETA;
  }
  if (asuntoLower.includes("pago inmediato en banco venezolano")) {
    return TIPO_PAGO_INMEDIATO;
  }
  if (asuntoLower.includes("transferencia a tercero")) {
    return TIPO_TRANSFERENCIA;
  }
  if (asuntoLower.includes("pago de servicio")) {
    return TIPO_SERVICIO;
  }
  if (
    asuntoLower.includes("pago móvil bvc") ||
    asuntoLower.includes("pago movil bvc")
  ) {
    if (cuerpoLower.includes("ha recibido un pago")) {
      return TIPO_RECIBIDO;
    }
    if (cuerpoLower.includes("hemos registrado un pago")) {
      return TIPO_ENVIADO;
    }
  }
  return TIPO_DESCONOCIDO;
}

// ─── Helpers internos ────────────────────────────────────────────────────────

/** Busca un patrón regex y retorna el grupo 1, o null */
function _buscar(patron: string, texto: string): string | null {
  const m = new RegExp(patron, "is").exec(texto);
  return m ? m[1].trim() : null;
}

/**
 * Limpia un monto en formato venezolano 1.234,56 → 1234.56
 * Split por coma: si 2 partes → entero.decimal. Si no → quitar puntos y espacios.
 */
function _limpiarMonto(texto: string): number | null {
  if (!texto) return null;
  let limpio = texto.trim();
  const partes = limpio.split(",");
  if (partes.length === 2) {
    const entero = partes[0].replace(/\./g, "").replace(/ /g, "");
    const decimal = partes[1].trim();
    limpio = `${entero}.${decimal}`;
  } else {
    limpio = limpio.replace(/\./g, "").replace(/ /g, "");
  }
  const num = parseFloat(limpio);
  return isNaN(num) ? null : num;
}

/**
 * Parsea fecha manualmente: DD/MM/YYYY HH:MM:SS, DD/MM/YYYY HH:MM AM/PM,
 * DD/MM/YYYY HH:MM
 */
function _parsearFecha(fechaStr: string, horaStr: string): Date | null {
  const f = fechaStr.trim();
  const h = horaStr.trim();
  const texto = `${f} ${h}`;

  // Intentar DD/MM/YYYY HH:MM:SS
  let m = /^(\d{2})\/(\d{2})\/(\d{4})\s+(\d{1,2}):(\d{2}):(\d{2})$/.exec(texto);
  if (m) {
    return desdeHoraVE(
      parseInt(m[3]), parseInt(m[2]) - 1, parseInt(m[1]),
      parseInt(m[4]), parseInt(m[5]), parseInt(m[6])
    );
  }

  // Intentar DD/MM/YYYY HH:MM AM/PM
  m = /^(\d{2})\/(\d{2})\/(\d{4})\s+(\d{1,2}):(\d{2})\s*(AM|PM)$/i.exec(texto);
  if (m) {
    let hora = parseInt(m[4]);
    const ampm = m[6].toUpperCase();
    if (ampm === "PM" && hora !== 12) hora += 12;
    if (ampm === "AM" && hora === 12) hora = 0;
    return desdeHoraVE(
      parseInt(m[3]), parseInt(m[2]) - 1, parseInt(m[1]),
      hora, parseInt(m[5]), 0
    );
  }

  // Intentar DD/MM/YYYY HH:MM
  m = /^(\d{2})\/(\d{2})\/(\d{4})\s+(\d{1,2}):(\d{2})$/.exec(texto);
  if (m) {
    return desdeHoraVE(
      parseInt(m[3]), parseInt(m[2]) - 1, parseInt(m[1]),
      parseInt(m[4]), parseInt(m[5]), 0
    );
  }

  return null;
}

// ─── Parsers por tipo de correo ──────────────────────────────────────────────

export function parsearRecibido(cuerpo: string): DatosParseo {
  const resultado: DatosParseo = {
    tipo: "entrada",
    subtipo: TIPO_RECIBIDO,
    monto_bs: null,
    celular_origen: null,
    fecha: null,
    referencia: null,
  };

  const rawMonto = _buscar(String.raw`pago por\s+Bs\.\s*([\d\s.,]+?)\s*a través`, cuerpo);
  if (rawMonto) {
    resultado.monto_bs = _limpiarMonto(rawMonto);
  }

  const rawCelular = _buscar(String.raw`número de celular\s+(\*[\d*\-]+)`, cuerpo);
  if (rawCelular) {
    resultado.celular_origen = rawCelular;
  }

  const mFecha = new RegExp(
    String.raw`el día\s+(\d{2}/\d{2}/\d{4})\s+a las\s+([\d:]+)`,
    "i"
  ).exec(cuerpo);
  if (mFecha) {
    resultado.fecha = _parsearFecha(mFecha[1], mFecha[2]);
  }

  const rawRef = _buscar(String.raw`código de referencia\s+(\d+)`, cuerpo);
  if (rawRef) {
    resultado.referencia = rawRef;
  }

  return resultado;
}

export function parsearEnviado(cuerpo: string): DatosParseo {
  const resultado: DatosParseo = {
    tipo: "salida",
    subtipo: TIPO_ENVIADO,
    monto_bs: null,
    contacto_destino: null,
    fecha: null,
    referencia: null,
  };

  const rawMonto = _buscar(String.raw`pago por\s+Bs\.\s*([\d\s.,]+?)\s*a través`, cuerpo);
  if (rawMonto) {
    resultado.monto_bs = _limpiarMonto(rawMonto);
  }

  const rawCelular = _buscar(String.raw`número de celular\s+(\*[\d*\-]+)`, cuerpo);
  if (rawCelular) {
    resultado.contacto_destino = rawCelular;
  }

  const mFecha = new RegExp(
    String.raw`el día\s+(\d{2}/\d{2}/\d{4})\s+a las\s+([\d:]+)`,
    "i"
  ).exec(cuerpo);
  if (mFecha) {
    resultado.fecha = _parsearFecha(mFecha[1], mFecha[2]);
  }

  const rawRef = _buscar(String.raw`código de referencia\s+(\d+)`, cuerpo);
  if (rawRef) {
    resultado.referencia = rawRef;
  }

  return resultado;
}

export function parsearTransferencia(cuerpo: string): DatosParseo {
  const resultado: DatosParseo = {
    tipo: "salida",
    subtipo: TIPO_TRANSFERENCIA,
    monto_bs: null,
    comision_declarada_bs: null,
    contacto_destino: null,
    banco_destino: null,
    beneficiario: null,
    concepto: null,
    fecha: null,
    referencia: null,
  };

  let raw = _buscar(String.raw`Monto a Debitar[:\s]+([\d.,]+)`, cuerpo);
  if (raw) resultado.monto_bs = _limpiarMonto(raw);

  raw = _buscar(String.raw`Comision[:\s]+([\d.,]+)`, cuerpo);
  if (raw) resultado.comision_declarada_bs = _limpiarMonto(raw);

  raw = _buscar(String.raw`Tel[eé?]+fono Destino[:\s]+(\d+)`, cuerpo);
  if (raw) resultado.contacto_destino = raw;

  raw = _buscar(String.raw`Banco Destino[:\s]+(.+?)(?:\s+Monto a Acreditar|\n|$)`, cuerpo);
  if (raw) resultado.banco_destino = raw;

  raw = _buscar(String.raw`Nombre del Beneficiario[:\s]+(.+?)(?:\s+Banco Destino|\n|$)`, cuerpo);
  if (raw) resultado.beneficiario = raw;

  raw = _buscar(String.raw`Concepto del Pago[:\s]+(.+?)(?:\s+Referencia|\n|$)`, cuerpo);
  if (raw) resultado.concepto = raw;

  const mFecha = new RegExp(
    String.raw`Fecha y Hora[:\s]+(\d{2}/\d{2}/\d{4})\s+([\d:]+\s*(?:[AP]M)?)`,
    "i"
  ).exec(cuerpo);
  if (mFecha) {
    resultado.fecha = _parsearFecha(mFecha[1], mFecha[2].trim());
  }

  raw = _buscar(String.raw`Referencia[:\s]+(\d+)`, cuerpo);
  if (raw) resultado.referencia = raw;

  return resultado;
}

export function parsearPagoInmediato(cuerpo: string): DatosParseo {
  const resultado: DatosParseo = {
    tipo: "salida",
    subtipo: TIPO_PAGO_INMEDIATO,
    monto_bs: null,
    referencia: null,
    concepto: null,
    contacto_destino: null,
    banco_destino: null,
    fecha: null,
  };

  let raw = _buscar(String.raw`Monto a Debitar[:\s]+([\d.,]+)`, cuerpo);
  if (raw) resultado.monto_bs = _limpiarMonto(raw);

  raw = _buscar(String.raw`Referencia[:\s]+(\d+)`, cuerpo);
  if (raw) resultado.referencia = raw;

  raw = _buscar(String.raw`Concepto del Pago[:\s]+(.+?)(?:\s+Referencia|\n|$)`, cuerpo);
  if (raw) resultado.concepto = raw;

  raw = _buscar(String.raw`Tel[eé?]+fono Destino[:\s]+(\d+)`, cuerpo);
  if (raw) resultado.contacto_destino = raw;

  raw = _buscar(String.raw`Banco Destino[:\s]+(.+?)(?:\s+Monto a Acreditar|\n|$)`, cuerpo);
  if (raw) resultado.banco_destino = raw;

  const mFecha = new RegExp(
    String.raw`Fecha y Hora[:\s]+(\d{2}/\d{2}/\d{4})\s+([\d:]+\s*(?:[AP]M)?)`,
    "i"
  ).exec(cuerpo);
  if (mFecha) {
    resultado.fecha = _parsearFecha(mFecha[1], mFecha[2].trim());
  }

  return resultado;
}

export function parsearTarjeta(cuerpo: string): DatosParseo {
  const resultado: DatosParseo = {
    tipo: "salida",
    subtipo: TIPO_TARJETA,
    monto_bs: null,
    tarjeta_ultimos: null,
    comercio: null,
    fecha: null,
    referencia: null,
    etiquetas: [],
  };

  // Monto — "Bs       6.880,00"
  let raw = _buscar(String.raw`monto de Bs\s+([\d\s.,]+?)\s+realizada`, cuerpo);
  if (raw) resultado.monto_bs = _limpiarMonto(raw);

  // Tarjeta — últimos dígitos "****-****-**12-1724"
  raw = _buscar(String.raw`tarjeta No\.\s+([\*\-\d]+)`, cuerpo);
  if (raw) resultado.tarjeta_ultimos = raw;

  // Fecha y hora "el día 09/06/2026 a las 17:22:17"
  const mFecha = new RegExp(
    String.raw`el día\s+(\d{2}/\d{2}/\d{4})\s+a las\s+([\d:]+)`,
    "i"
  ).exec(cuerpo);
  if (mFecha) {
    resultado.fecha = _parsearFecha(mFecha[1], mFecha[2]);
  }

  // Comercio — entre "en el comercio" y el código VE o aprobación
  raw = _buscar(String.raw`en el comercio\s+(.+?)\s+(?:VE\b|la cual)`, cuerpo);
  if (raw) resultado.comercio = raw.trim();

  // Código de aprobación → guardado como referencia y como etiqueta
  raw = _buscar(String.raw`aprobada con código\s+(\d+)`, cuerpo);
  if (raw) {
    resultado.referencia = raw;
    resultado.etiquetas = [`aprobacion:${raw}`];
  }

  return resultado;
}

export function parsearServicio(cuerpo: string): DatosParseo {
  const resultado: DatosParseo = {
    tipo: "salida",
    subtipo: TIPO_SERVICIO,
    monto_bs: null,
    contacto_destino: null,
    fecha: null,
    referencia: null,
  };

  // Monto — maneja "Bs. 600" y "Bs. 600,00"
  const rawMonto = _buscar(String.raw`monto de Bs\.\s*([\d.,]+)`, cuerpo);
  if (rawMonto) {
    // Si no tiene coma, es entero — agregamos .00
    if (!rawMonto.includes(",")) {
      const parsed = parseFloat(rawMonto.replace(/\./g, "").trim());
      if (!isNaN(parsed)) resultado.monto_bs = parsed;
    } else {
      resultado.monto_bs = _limpiarMonto(rawMonto);
    }
  }

  // Número de servicio (teléfono, cuenta, etc.)
  const rawServicio = _buscar(String.raw`servicio Nro\.\s*([\d]+)`, cuerpo);
  if (rawServicio) {
    resultado.contacto_destino = rawServicio;
  }

  // Fecha y hora: "11/06/2026 08:24 AM"
  const mFecha = new RegExp(
    String.raw`fecha y hora\s+(\d{2}/\d{2}/\d{4})\s+([\d:]+\s*(?:[AP]M)?)`,
    "i"
  ).exec(cuerpo);
  if (mFecha) {
    resultado.fecha = _parsearFecha(mFecha[1], mFecha[2].trim());
  }

  return resultado;
}

// ─── Router principal ────────────────────────────────────────────────────────

export function parsearCorreo(asunto: string, cuerpo: string): DatosParseo {
  const tipo = identificarTipo(asunto, cuerpo);

  if (tipo === "rechazado") {
    const datos = parsearEnviado(cuerpo);
    datos.tipo = "rechazado";
    datos.subtipo = "rechazado";
    return datos;
  } else if (tipo === TIPO_TARJETA) {
    return parsearTarjeta(cuerpo);
  } else if (tipo === TIPO_PAGO_INMEDIATO) {
    return parsearPagoInmediato(cuerpo);
  } else if (tipo === TIPO_SERVICIO) {
    return parsearServicio(cuerpo);
  } else if (tipo === TIPO_RECIBIDO) {
    return parsearRecibido(cuerpo);
  } else if (tipo === TIPO_ENVIADO) {
    return parsearEnviado(cuerpo);
  } else if (tipo === TIPO_TRANSFERENCIA) {
    return parsearTransferencia(cuerpo);
  } else {
    return { tipo: "desconocido", subtipo: TIPO_DESCONOCIDO, monto_bs: null, referencia: null, fecha: null };
  }
}
