// ─── Interfaces del dominio BankTrack ─────────────────────────────────────────

/** Correo crudo leído de Gmail */
export interface Correo {
  id: string;
  asunto: string;
  cuerpo: string;
}

/** Resultado del parseo de un correo bancario */
export interface DatosParseo {
  tipo: string;
  subtipo: string;
  monto_bs: number | null;
  referencia: string | null;
  fecha: Date | null;
  celular_origen?: string | null;
  contacto_destino?: string | null;
  banco_destino?: string | null;
  beneficiario?: string | null;
  concepto?: string | null;
  comercio?: string | null;
  tarjeta_ultimos?: string | null;
  etiquetas?: string[];
  comision_declarada_bs?: number | null;
}

/** Resultado del cálculo de comisión */
export interface Comision {
  monto: number;
  fuente: string | null;
}

/** Registro listo para insertar en Supabase */
export interface Registro {
  email_id: string;
  fecha: string;
  tipo: string;
  subtipo: string;
  monto_bs: number | null;
  tasa_dolar: number | null;
  monto_usd: number | null;
  tasa_euro: number | null;
  monto_eur: number | null;
  referencia: string | null;
  celular_origen: string | null;
  contacto_destino: string | null;
  banco_destino: string | null;
  beneficiario: string | null;
  comercio: string | null;
  tarjeta_ultimos: string | null;
  comision_bs: number;
  comision_fuente: string | null;
  mes_corte: string;
  concepto: string | null;
  etiquetas: string[];
}
