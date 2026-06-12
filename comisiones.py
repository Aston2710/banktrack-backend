def calcular_comision_pagomovil(monto_bs: float) -> float:
    """
    Regla BVC pagomóvil:
    - 0.3% del monto
    - Mínimo 2 Bs
    """
    comision = round(monto_bs * 0.003, 2)
    return max(comision, 2.0)


def resolver_comision(transaccion: dict) -> dict:
    """
    Retorna {"monto": float, "fuente": str|None}
    - transferencia → monto declarado por el banco, fuente "declarada"
    - enviado       → calcula 0.3% con mínimo 2 Bs, fuente "calculada"
    - servicio      → 0.0, fuente "exonerada" (regulación BCV)
    - rechazado/entradas/otros → 0.0 o tarifa plana, fuente None
    """
    subtipo = transaccion.get("subtipo")
    monto   = transaccion.get("monto_bs") or 0.0

    if subtipo == "transferencia":
        monto_com = transaccion.get("comision_declarada_bs") or 0.0
        return {"monto": monto_com, "fuente": "declarada"}
    elif subtipo == "enviado":
        return {"monto": calcular_comision_pagomovil(monto), "fuente": "calculada"}
    elif subtipo == "rechazado":
        return {"monto": 2.0, "fuente": None}
    elif subtipo == "servicio":
        return {"monto": 0.0, "fuente": "exonerada"}
    else:
        return {"monto": 0.0, "fuente": None}