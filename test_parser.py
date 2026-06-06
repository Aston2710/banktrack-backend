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
        "nombre": "TRANSFERENCIA (todo en una línea como llega del banco)",
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
]

for caso in casos:
    print(f"\n{'='*55}")
    print(f"  CASO: {caso['nombre']}")
    print('='*55)
    resultado = parsear_correo(caso["asunto"], caso["cuerpo"])
    for k, v in resultado.items():
        print(f"  {k:28} → {v}")