import re
from datetime import datetime
from typing import Optional

TIPO_RECIBIDO       = "recibido"
TIPO_ENVIADO        = "enviado"
TIPO_TRANSFERENCIA  = "transferencia"
TIPO_PAGO_INMEDIATO = "pago_inmediato"
TIPO_TARJETA        = "tarjeta"
TIPO_DESCONOCIDO    = "desconocido"
TIPO_SERVICIO = "servicio"

def identificar_tipo(asunto: str, cuerpo: str) -> str:
    asunto_lower = asunto.lower()
    cuerpo_lower = cuerpo.lower()

    if "fue rechazado" in cuerpo_lower:
        return "rechazado"
    if "notificación de uso de su tarjeta" in asunto_lower or \
       "notificacion de uso de su tarjeta" in asunto_lower:
        return TIPO_TARJETA
    if "pago inmediato en banco venezolano" in asunto_lower:
        return TIPO_PAGO_INMEDIATO
    if "transferencia a tercero" in asunto_lower:
        return TIPO_TRANSFERENCIA
    if "pago de servicio" in asunto_lower:          # ← NUEVO
        return TIPO_SERVICIO
    if "pago móvil bvc" in asunto_lower or "pago movil bvc" in asunto_lower:
        if "ha recibido un pago" in cuerpo_lower:
            return TIPO_RECIBIDO
        if "hemos registrado un pago" in cuerpo_lower:
            return TIPO_ENVIADO
    return TIPO_DESCONOCIDO


def _limpiar_monto(texto: str) -> Optional[float]:
    if not texto:
        return None
    limpio = texto.strip()
    partes = limpio.split(',')
    if len(partes) == 2:
        entero  = partes[0].replace('.', '').replace(' ', '')
        decimal = partes[1].strip()
        limpio  = f"{entero}.{decimal}"
    else:
        limpio = limpio.replace('.', '').replace(' ', '')
    try:
        return float(limpio)
    except ValueError:
        return None


def _parsear_fecha(fecha_str: str, hora_str: str) -> Optional[datetime]:
    formatos = [
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %I:%M %p",
        "%d/%m/%Y %H:%M",
    ]
    texto = f"{fecha_str.strip()} {hora_str.strip()}"
    for fmt in formatos:
        try:
            return datetime.strptime(texto, fmt)
        except ValueError:
            continue
    return None

def parsear_servicio(cuerpo: str) -> dict:
    """
    Pago de servicio (recarga telefónica, luz, etc.)
    Sin comisión por regulación BCV.
    Monto puede venir con o sin decimales: "Bs. 600" o "Bs. 600,00"
    """
    resultado = {
        "tipo":             "salida",
        "subtipo":          TIPO_SERVICIO,
        "monto_bs":         None,
        "numero_servicio":  None,
        "fecha":            None,
        "referencia":       None,
    }

    # Monto — maneja "Bs. 600" y "Bs. 600,00"
    raw = _buscar(r'monto de Bs\.\s*([\d.,]+)', cuerpo)
    if raw:
        # Si no tiene coma, es entero — agregamos .00
        if ',' not in raw:
            try:
                resultado["monto_bs"] = float(raw.replace('.', '').strip())
            except ValueError:
                pass
        else:
            resultado["monto_bs"] = _limpiar_monto(raw)

    # Número de servicio (teléfono, cuenta, etc.)
    raw = _buscar(r'servicio Nro\.\s*([\d]+)', cuerpo)
    if raw:
        resultado["numero_servicio"] = raw

    # Fecha y hora: "11/06/2026 08:24 AM"
    m = re.search(
        r'fecha y hora\s+(\d{2}/\d{2}/\d{4})\s+([\d:]+\s*(?:[AP]M)?)',
        cuerpo, re.IGNORECASE
    )
    if m:
        resultado["fecha"] = _parsear_fecha(m.group(1), m.group(2).strip())

    return resultado


def _buscar(patron: str, texto: str) -> Optional[str]:
    m = re.search(patron, texto, re.IGNORECASE | re.DOTALL)
    return m.group(1).strip() if m else None


def parsear_recibido(cuerpo: str) -> dict:
    resultado = {
        "tipo":           "entrada",
        "subtipo":        TIPO_RECIBIDO,
        "monto_bs":       None,
        "celular_origen": None,
        "fecha":          None,
        "referencia":     None,
    }

    raw = _buscar(r'pago por\s+Bs\.\s*([\d\s.,]+?)\s*a través', cuerpo)
    if raw:
        resultado["monto_bs"] = _limpiar_monto(raw)

    raw = _buscar(r'número de celular\s+(\*[\d*\-]+)', cuerpo)
    if raw:
        resultado["celular_origen"] = raw

    m = re.search(
        r'el día\s+(\d{2}/\d{2}/\d{4})\s+a las\s+([\d:]+)',
        cuerpo, re.IGNORECASE
    )
    if m:
        resultado["fecha"] = _parsear_fecha(m.group(1), m.group(2))

    raw = _buscar(r'código de referencia\s+(\d+)', cuerpo)
    if raw:
        resultado["referencia"] = raw

    return resultado


def parsear_enviado(cuerpo: str) -> dict:
    resultado = {
        "tipo":            "salida",
        "subtipo":         TIPO_ENVIADO,
        "monto_bs":        None,
        "celular_destino": None,
        "fecha":           None,
        "referencia":      None,
    }

    raw = _buscar(r'pago por\s+Bs\.\s*([\d\s.,]+?)\s*a través', cuerpo)
    if raw:
        resultado["monto_bs"] = _limpiar_monto(raw)

    raw = _buscar(r'número de celular\s+(\*[\d*\-]+)', cuerpo)
    if raw:
        resultado["celular_destino"] = raw

    m = re.search(
        r'el día\s+(\d{2}/\d{2}/\d{4})\s+a las\s+([\d:]+)',
        cuerpo, re.IGNORECASE
    )
    if m:
        resultado["fecha"] = _parsear_fecha(m.group(1), m.group(2))

    raw = _buscar(r'código de referencia\s+(\d+)', cuerpo)
    if raw:
        resultado["referencia"] = raw

    return resultado


def parsear_transferencia(cuerpo: str) -> dict:
    resultado = {
        "tipo":                  "salida",
        "subtipo":               TIPO_TRANSFERENCIA,
        "monto_bs":              None,
        "comision_declarada_bs": None,
        "telefono_destino":      None,
        "banco_destino":         None,
        "beneficiario":          None,
        "concepto":              None,
        "fecha":                 None,
        "referencia":            None,
    }

    raw = _buscar(r'Monto a Debitar[:\s]+([\d.,]+)', cuerpo)
    if raw:
        resultado["monto_bs"] = _limpiar_monto(raw)

    raw = _buscar(r'Comision[:\s]+([\d.,]+)', cuerpo)
    if raw:
        resultado["comision_declarada_bs"] = _limpiar_monto(raw)

    raw = _buscar(r'Tel[eé?]+fono Destino[:\s]+(\d+)', cuerpo)
    if raw:
        resultado["telefono_destino"] = raw

    raw = _buscar(r'Banco Destino[:\s]+(.+?)(?:\s+Monto a Acreditar|\n|$)', cuerpo)
    if raw:
        resultado["banco_destino"] = raw

    raw = _buscar(r'Nombre del Beneficiario[:\s]+(.+?)(?:\s+Banco Destino|\n|$)', cuerpo)
    if raw:
        resultado["beneficiario"] = raw

    raw = _buscar(r'Concepto del Pago[:\s]+(.+?)(?:\s+Referencia|\n|$)', cuerpo)
    if raw:
        resultado["concepto"] = raw

    m = re.search(
        r'Fecha y Hora[:\s]+(\d{2}/\d{2}/\d{4})\s+([\d:]+\s*(?:[AP]M)?)',
        cuerpo, re.IGNORECASE
    )
    if m:
        resultado["fecha"] = _parsear_fecha(m.group(1), m.group(2).strip())

    raw = _buscar(r'Referencia[:\s]+(\d+)', cuerpo)
    if raw:
        resultado["referencia"] = raw

    return resultado


def parsear_pago_inmediato(cuerpo: str) -> dict:
    resultado = {
        "tipo":             "enriquecimiento",
        "subtipo":          TIPO_PAGO_INMEDIATO,
        "monto_bs":         None,
        "referencia":       None,
        "concepto":         None,
        "telefono_destino": None,
        "banco_destino":    None,
        "fecha":            None,
    }

    raw = _buscar(r'Monto a Debitar[:\s]+([\d.,]+)', cuerpo)
    if raw:
        resultado["monto_bs"] = _limpiar_monto(raw)

    raw = _buscar(r'Referencia[:\s]+(\d+)', cuerpo)
    if raw:
        resultado["referencia"] = raw

    raw = _buscar(r'Concepto del Pago[:\s]+(.+?)(?:\s+Referencia|\n|$)', cuerpo)
    if raw:
        resultado["concepto"] = raw

    raw = _buscar(r'Tel[eé?]+fono Destino[:\s]+(\d+)', cuerpo)
    if raw:
        resultado["telefono_destino"] = raw

    raw = _buscar(r'Banco Destino[:\s]+(.+?)(?:\s+Monto a Acreditar|\n|$)', cuerpo)
    if raw:
        resultado["banco_destino"] = raw

    m = re.search(
        r'Fecha y Hora[:\s]+(\d{2}/\d{2}/\d{4})\s+([\d:]+\s*(?:[AP]M)?)',
        cuerpo, re.IGNORECASE
    )
    if m:
        resultado["fecha"] = _parsear_fecha(m.group(1), m.group(2).strip())

    return resultado


def parsear_tarjeta(cuerpo: str) -> dict:
    resultado = {
        "tipo":            "salida",
        "subtipo":         TIPO_TARJETA,
        "monto_bs":        None,
        "tarjeta_ultimos": None,
        "comercio":        None,
        "fecha":           None,
        "referencia":      None,  # código de aprobación como referencia
        "etiquetas":       [],
    }

    # Monto — "Bs       6.880,00"
    raw = _buscar(r'monto de Bs\s+([\d\s.,]+?)\s+realizada', cuerpo)
    if raw:
        resultado["monto_bs"] = _limpiar_monto(raw)

    # Tarjeta — últimos dígitos "****-****-**12-1724"
    raw = _buscar(r'tarjeta No\.\s+([\*\-\d]+)', cuerpo)
    if raw:
        resultado["tarjeta_ultimos"] = raw

    # Fecha y hora "el día 09/06/2026 a las 17:22:17"
    m = re.search(
        r'el día\s+(\d{2}/\d{2}/\d{4})\s+a las\s+([\d:]+)',
        cuerpo, re.IGNORECASE
    )
    if m:
        resultado["fecha"] = _parsear_fecha(m.group(1), m.group(2))

    # Comercio — entre "en el comercio" y el código VE o aprobación
    raw = _buscar(r'en el comercio\s+(.+?)\s+(?:VE\b|la cual)', cuerpo)
    if raw:
        resultado["comercio"] = raw.strip()

    # Código de aprobación → guardado como referencia y como etiqueta
    raw = _buscar(r'aprobada con código\s+(\d+)', cuerpo)
    if raw:
        resultado["referencia"] = raw
        resultado["etiquetas"]  = [f"aprobacion:{raw}"]

    return resultado


def parsear_correo(asunto: str, cuerpo: str) -> dict:
    tipo = identificar_tipo(asunto, cuerpo)

    if tipo == "rechazado":
        datos = parsear_enviado(cuerpo)
        datos["tipo"]    = "rechazado"
        datos["subtipo"] = "rechazado"
        return datos
    elif tipo == TIPO_TARJETA:
        return parsear_tarjeta(cuerpo)
    elif tipo == TIPO_PAGO_INMEDIATO:
        return parsear_pago_inmediato(cuerpo)
    elif tipo == TIPO_SERVICIO:
        return parsear_servicio(cuerpo)
    elif tipo == TIPO_RECIBIDO:
        return parsear_recibido(cuerpo)
    elif tipo == TIPO_ENVIADO:
        return parsear_enviado(cuerpo)
    elif tipo == TIPO_TRANSFERENCIA:
        return parsear_transferencia(cuerpo)
    else:
        return {"tipo": "desconocido", "subtipo": TIPO_DESCONOCIDO}