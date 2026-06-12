from parser import parsear_correo

casos = [
    {
        "nombre": "RECIBIDO",
        "asunto": "Notificación de operación efectuada a través del servicio Pago Móvil BVC.",
        "cuerpo": (
            "Estimado cliente, le notificamos que Usted ha recibido un pago por Bs.           1,00 "
            "a través de nuestro servicio Pago Móvil BVC, realizada desde el número de celular "
            "****-*****82, el día 05/06/2026 a las 19:59:07, con código de referencia 00123456\n"
            "Para mayor información comuníquese al 0501-mibanco (0501-642.2626), "
            "0212-203.5300 o *BVC (282) para Movilnet / Movistar.\n"
            "Gracias por usar nuestros servicios.\n"
            "VENEZOLANO DE CREDITO, S.A. Banco Universal"
        ),
    },
    {
        "nombre": "ENVIADO",
        "asunto": "Notificación de operación efectuada a través de nuestro servicio Pago Móvil BVC.",
        "cuerpo": (
            "Estimado cliente, le notificamos que hemos registrado un pago por Bs.       1.234,00 "
            "a través de nuestro servicio Pago Móvil BVC, realizada para el número de celular "
            "****-*****98, el día 05/06/2026 a las 09:52:14, con código de referencia 00765432.\n"
            "Para mayor información comuníquese al 0501-mibanco (0501-642.2626), "
            "0212-203.5300 o *BVC (282) para Movilnet / Movistar.\n"
            "Gracias por usar nuestros servicios.\n"
            "VENEZOLANO DE CREDITO, S.A. Banco Universal"
        ),
    },
    {
        "nombre": "TRANSFERENCIA",
        "asunto": "Transferencia a Tercero en otro Banco en el Sistema Venezolano Online con disponibilidad inmediata",
        "cuerpo": (
            "Estimado cliente, le notificamos que hemos registrado una transaccion de: "
            "Transferencia a Tercero en otro Banco en el Sistema Venezolano Online con disponibilidad inmediata "
            "Fecha y Hora: 02/06/2026 08:05 AM Usuario: AB****CD Cuenta Origen: ****************1234 "
            "Monto a Debitar: 38.894,59 Comision: 116,68 Teléfono Destino: 04121234567 "
            "Nombre del Beneficiario: Transferencia Banco Destino: BANCO DE VENEZUELA "
            "Monto a Acreditar: 38.894,59 Concepto del Pago: Mov Referencia: 00123456 "
            "Descubra las ventajas de Venezolano Online y realice sus transacciones con máxima seguridad y rapidez."
        ),
    },
    {
        "nombre": "RECHAZADO",
        "asunto": "Notificación de operación efectuada a través de nuestro servicio Pago Móvil BVC.",
        "cuerpo": (
            "Estimado cliente, le notificamos que hemos registrado un pago por Bs.        1,00 "
            "a través de nuestro servicio Pago Móvil BVC, realizada para el número de celular "
            "****-*****92, el día 01/06/2026 a las 23:50:05, el cual fue rechazado.\n"
            "Para mayor información comuníquese al 0501-mibanco (0501-642.2626), "
            "0212-203.5300 o *BVC (282) para Movilnet / Movistar.\n"
            "Gracias por usar nuestros servicios.\n"
            "VENEZOLANO DE CREDITO, S.A. Banco Universal"
        ),
    },
    {
        "nombre": "PAGO INMEDIATO",
        "asunto": "Pago Inmediato en Banco Venezolano de Cr?dito a trav?s del Sistema Venezolano Online",
        "cuerpo": (
            "Estimado cliente, le notificamos que hemos registrado una transaccion de: "
            "Pago Inmediato en el Sistema Venezolano Online\n"
            "Fecha y Hora: 05/06/2026 21:41\n"
            "Usuario: JE****RM\n"
            "Cuenta Origen: 000157024388\n"
            "Monto a Debitar: 5,00\n"
            "Tel?fono Destino: 04144415089\n"
            "Nombre del Beneficiario: Pago Movil\n"
            "Banco Destino: BANCO DEL CARIBE, C.A. BANCO UNIV\n"
            "Monto a Acreditar: 5,00\n"
            "Concepto del Pago: Si\n"
            "Referencia: 00455175"
        ),
    },
    {
        "nombre": "TARJETA",
        "asunto": "Notificación de uso de su tarjeta del Venezolano de Crédito",
        "cuerpo": (
            "Estimado cliente, le notificamos que hemos registrado una transacción de consumo "
            "por un monto de Bs       6.880,00 realizada con su tarjeta No. ****-****-**12-1724, "
            "el día 09/06/2026 a las 17:22:17 en el comercio PERFUMERIA ALI BABA, C,A CARABOBO     "
            "VE la cual fue aprobada con código 221696.\n"
            "Para mayor información comuníquese al 0501-mibanco (0501-642.2626), "
            "0212-203.5300 o *BVC (282) para Movilnet / Movistar.\n"
            "Gracias por usar nuestros servicios.\n"
            "VENEZOLANO DE CREDITO, S.A. Banco Universal"
        ),
    },
    {
        "nombre": "SERVICIO",
        "asunto": "Pago de Servicio",
        "cuerpo": (
            "Estimado cliente, le notificamos que hemos registrado un pago de servicio "
            "Nro. 04125067692 a traves del Venezolano de Credito por Venezolano Online, "
            "por un monto de Bs. 600, en fecha y hora 11/06/2026 08:24 AM\n"
            "Si Usted no reconoce este pago de servicio por Venezolano Online, "
            "por favor comuniquese con el 0501-mibanco(6422626) o 0212-203.5300.\n"
            "Gracias por utilizar el Venezolano Online."
        ),
    },
]

# Campos mínimos esperados por tipo
campos_requeridos = {
    "RECIBIDO":       ["monto_bs", "fecha", "referencia"],
    "ENVIADO":        ["monto_bs", "fecha", "referencia"],
    "TRANSFERENCIA":  ["monto_bs", "fecha", "referencia", "concepto"],
    "RECHAZADO":      ["monto_bs", "fecha"],
    "PAGO INMEDIATO": ["monto_bs", "fecha", "referencia", "concepto"],
    "TARJETA":        ["monto_bs", "fecha", "comercio", "tarjeta_ultimos"],
    "SERVICIO": ["monto_bs", "fecha", "numero_servicio"],
}

errores_total = 0
for caso in casos:
    print(f"\n{'='*55}")
    print(f"  CASO: {caso['nombre']}")
    print('='*55)
    resultado = parsear_correo(caso["asunto"], caso["cuerpo"])
    for k, v in resultado.items():
        print(f"  {k:28} → {v}")

    requeridos = campos_requeridos.get(caso["nombre"], [])
    errores_caso = 0
    for campo in requeridos:
        if not resultado.get(campo):
            print(f"  ❌ FALTA: {campo}")
            errores_caso += 1
    if errores_caso == 0:
        print(f"  ✅ OK")
    errores_total += errores_caso

print(f"\n{'='*55}")
print(f"  TOTAL errores: {errores_total}")
print(f"  {'✅ Todos los casos pasan' if errores_total == 0 else '❌ Hay errores que corregir'}")