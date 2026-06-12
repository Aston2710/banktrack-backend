def calcular_comision_pagomovil(monto_bs: float) -> float:
    """
    Regla BVC pagomóvil:
    - 0.3% del monto
    - Mínimo 2 Bs
    """
    comision = round(monto_bs * 0.003, 2)
    return max(comision, 2.0)


def resolver_comision(transaccion: dict) -> float:
    """
    - transferencia → usa la comisión declarada por el banco
    - enviado       → calcula 0.3% con mínimo 2 Bs
    - entrada       → sin comisión
    """
    subtipo = transaccion.get("subtipo")
    monto   = transaccion.get("monto_bs") or 0.0

    if subtipo == "transferencia":
        return transaccion.get("comision_declarada_bs") or 0.0
    elif subtipo == "enviado":
        return calcular_comision_pagomovil(monto)
    elif subtipo == "rechazado":
        return 2.0
    elif subtipo == "servicio":
        return 0.0          # exonerado por regulación BCV
    else:
        return 0.0