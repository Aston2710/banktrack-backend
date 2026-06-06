import re
from datetime import datetime
from typing import Optional

TIPO_RECIBIDO      = "recibido"
TIPO_ENVIADO       = "enviado"
TIPO_TRANSFERENCIA = "transferencia"
TIPO_DESCONOCIDO   = "desconocido"


def identificar_tipo(asunto: str, cuerpo: str) -> str:
    asunto_lower = asunto.lower()
    cuerpo_lower = cuerpo.lower()

    # PRIMERO — rechazos, antes que cualquier otra cosa
    if "fue rechazado" in cuerpo_lower:
        return "rechazado"

    if "transferencia a tercero" in asunto_lower:
        return TIPO_TRANSFERENCIA
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
    # Separador de miles es punto, decimal es coma → "38.894,59"
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


def _buscar(patron: str, texto: str) -> Optional[str]:
    """
    Búsqueda con re.IGNORECASE + re.DOTALL.
    Maneja saltos de línea y espacios múltiples dentro del patrón.
    """
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

    # Monto — puede tener espacios entre "Bs." y el número
    raw = _buscar(r'pago por\s+Bs\.\s*([\d\s.,]+?)\s*a través', cuerpo)
    if raw:
        resultado["monto_bs"] = _limpiar_monto(raw)

    # Celular origen
    raw = _buscar(r'número de celular\s+(\*[\d*\-]+)', cuerpo)
    if raw:
        resultado["celular_origen"] = raw

    # Fecha y hora
    m = re.search(
        r'el día\s+(\d{2}/\d{2}/\d{4})\s+a las\s+([\d:]+)',
        cuerpo, re.IGNORECASE
    )
    if m:
        resultado["fecha"] = _parsear_fecha(m.group(1), m.group(2))

    # Referencia
    raw = _buscar(r'código de referencia\s+(\d+)', cuerpo)
    if raw:
        resultado["referencia"] = raw

    return resultado


def parsear_enviado(cuerpo: str) -> dict:
    resultado = {
        "tipo":             "salida",
        "subtipo":          TIPO_ENVIADO,
        "monto_bs":         None,
        "celular_destino":  None,
        "fecha":            None,
        "referencia":       None,
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

    # Monto a Debitar — termina cuando encuentra el siguiente campo
    raw = _buscar(r'Monto a Debitar[:\s]+([\d.,]+)', cuerpo)
    if raw:
        resultado["monto_bs"] = _limpiar_monto(raw)

    raw = _buscar(r'Comision[:\s]+([\d.,]+)', cuerpo)
    if raw:
        resultado["comision_declarada_bs"] = _limpiar_monto(raw)

    raw = _buscar(r'Teléfono Destino[:\s]+(\d+)', cuerpo)
    if raw:
        resultado["telefono_destino"] = raw

    # Banco destino — termina en el siguiente campo "Monto a Acreditar"
    raw = _buscar(r'Banco Destino[:\s]+(.+?)(?:\s+Monto a Acreditar|\n|$)', cuerpo)
    if raw:
        resultado["banco_destino"] = raw

    # Beneficiario — termina en "Banco Destino"
    raw = _buscar(r'Nombre del Beneficiario[:\s]+(.+?)(?:\s+Banco Destino|\n|$)', cuerpo)
    if raw:
        resultado["beneficiario"] = raw

    # Concepto — útil para saber qué fue el pago
    raw = _buscar(r'Concepto del Pago[:\s]+(.+?)(?:\s+Referencia|\n|$)', cuerpo)
    if raw:
        resultado["concepto"] = raw

    # Fecha y hora: "02/06/2026 08:05 AM"
    m = re.search(
        r'Fecha y Hora[:\s]+(\d{2}/\d{2}/\d{4})\s+([\d:]+ [AP]M)',
        cuerpo, re.IGNORECASE
    )
    if m:
        resultado["fecha"] = _parsear_fecha(m.group(1), m.group(2))

    raw = _buscar(r'Referencia[:\s]+(\d+)', cuerpo)
    if raw:
        resultado["referencia"] = raw

    return resultado


def parsear_correo(asunto: str, cuerpo: str) -> dict:
    tipo = identificar_tipo(asunto, cuerpo)

    if tipo == "rechazado":
        datos = parsear_enviado(cuerpo)
        datos["tipo"] = "rechazado"
        datos["subtipo"] = "rechazado"
        return datos
    elif tipo == TIPO_RECIBIDO:
        return parsear_recibido(cuerpo)
    elif tipo == TIPO_ENVIADO:
        return parsear_enviado(cuerpo)
    elif tipo == TIPO_TRANSFERENCIA:
        return parsear_transferencia(cuerpo)
    else:
        return {"tipo": "desconocido", "subtipo": TIPO_DESCONOCIDO}