import sys

# ══════════════════════════════════════════════════════════
# TEST 1 — Parser
# ══════════════════════════════════════════════════════════
def test_parser():
    print("\n" + "═"*55)
    print("  TEST 1 — Parser")
    print("═"*55)

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

    campos_requeridos = {
        "RECIBIDO":       ["monto_bs", "fecha", "referencia"],
        "ENVIADO":        ["monto_bs", "fecha", "referencia"],
        "TRANSFERENCIA":  ["monto_bs", "fecha", "referencia", "concepto"],
        "RECHAZADO":      ["monto_bs", "fecha"],
        "PAGO INMEDIATO": ["monto_bs", "fecha", "referencia", "concepto"],
        "TARJETA":        ["monto_bs", "fecha", "comercio", "tarjeta_ultimos"],
        "SERVICIO": ["monto_bs", "fecha", "numero_servicio"],
    }

    errores = 0
    for caso in casos:
        resultado = parsear_correo(caso["asunto"], caso["cuerpo"])
        print(f"\n  ── {caso['nombre']} ──")
        for k, v in resultado.items():
            print(f"    {k:28} → {v}")

        requeridos   = campos_requeridos.get(caso["nombre"], [])
        errores_caso = sum(1 for c in requeridos if not resultado.get(c))
        for campo in requeridos:
            if not resultado.get(campo):
                print(f"    ❌ FALTA: {campo}")
        if errores_caso == 0:
            print(f"  ✅ OK")
        errores += errores_caso

    return errores == 0

# ══════════════════════════════════════════════════════════
# TEST 2 — Comisiones
# ══════════════════════════════════════════════════════════
def test_comisiones():
    print("\n" + "═"*55)
    print("  TEST 2 — Comisiones")
    print("═"*55)

    from comisiones import calcular_comision_pagomovil, resolver_comision

    casos = [
        # (monto, esperado)
        (1.00,      2.00),   # mínimo 2 Bs
        (100.00,    2.00),   # 0.3% = 0.30 → mínimo 2 Bs
        (667.00,    2.00),   # 0.3% = 2.001 → justo en el límite
        (1000.00,   3.00),   # 0.3% = 3.00
        (38894.59,  116.68), # caso real transferencia
    ]

    errores = 0
    for monto, esperado in casos:
        resultado = calcular_comision_pagomovil(monto)
        ok = abs(resultado - esperado) < 0.01
        estado = "✅" if ok else "❌"
        print(f"  {estado} Bs. {monto:>10,.2f} → comisión: {resultado:>8,.2f}  (esperado: {esperado:,.2f})")
        if not ok:
            errores += 1

    # Test resolver_comision por subtipo
    print()
    casos_subtipo = [
        {"subtipo": "recibido",      "monto_bs": 1000.0,   "esperado": 0.0},
        {"subtipo": "enviado",       "monto_bs": 1000.0,   "esperado": 3.0},
        {"subtipo": "transferencia", "monto_bs": 38894.59,
         "comision_declarada_bs": 116.68,                  "esperado": 116.68},
    ]
    for caso in casos_subtipo:
        resultado = resolver_comision(caso)
        ok = abs(resultado - caso["esperado"]) < 0.01
        estado = "✅" if ok else "❌"
        print(f"  {estado} subtipo={caso['subtipo']:15} → comisión: {resultado:>8,.2f}  (esperado: {caso['esperado']:,.2f})")
        if not ok:
            errores += 1

    return errores == 0


# ══════════════════════════════════════════════════════════
# TEST 3 — DolarAPI
# ══════════════════════════════════════════════════════════
def test_dolar_api():
    print("\n" + "═"*55)
    print("  TEST 3 — DolarAPI (tasa BCV)")
    print("═"*55)

    from dolar_api import obtener_tasa_bcv

    tasa = obtener_tasa_bcv()
    if tasa and tasa > 0:
        print(f"  ✅ Tasa BCV obtenida: Bs. {tasa:,.4f} por dólar")
        print(f"     Ejemplo: Bs. 1.000,00 = ${1000/tasa:.2f} USD")
        return True
    else:
        print("  ❌ No se pudo obtener la tasa")
        return False


# ══════════════════════════════════════════════════════════
# TEST 4 — Supabase
# ══════════════════════════════════════════════════════════
def test_supabase():
    print("\n" + "═"*55)
    print("  TEST 4 — Supabase (conexión y operaciones)")
    print("═"*55)

    from supabase_client import (
        obtener_configuracion,
        insertar_transaccion,
        obtener_transacciones_mes,
    )
    from datetime import datetime

    errores = 0

    # 4a — Configuración
    print("\n  4a. Leer configuración...")
    config = obtener_configuracion()
    if config:
        print(f"  ✅ Configuración OK: {config}")
    else:
        print("  ❌ No se pudo leer configuración")
        errores += 1

    # 4b — Insertar transacción de prueba
    print("\n  4b. Insertar transacción de prueba...")
    registro_prueba = {
        "email_id":   "test-email-id-000",
        "fecha":      datetime.utcnow().isoformat(),
        "tipo":       "entrada",
        "subtipo":    "recibido",
        "monto_bs":   1.00,
        "tasa_dolar": 560.37,
        "monto_usd":  round(1.00 / 560.37, 4),
        "referencia": "00000000",
        "comision_bs": 0.0,
        "mes_corte":  datetime.now().strftime("%Y-%m"),
    }
    insertado = insertar_transaccion(registro_prueba)
    if insertado:
        print("  ✅ Inserción OK")
    else:
        print("  ⚠️  Ya existía o hubo error (ver log arriba)")

    # 4c — Leer transacciones del mes actual
    print("\n  4c. Leer transacciones del mes actual...")
    mes = datetime.now().strftime("%Y-%m")
    transacciones = obtener_transacciones_mes(mes)
    if transacciones is not None:
        print(f"  ✅ Transacciones en {mes}: {len(transacciones)}")
        for t in transacciones[:3]:
            print(f"     • {t.get('subtipo'):15} Bs. {t.get('monto_bs'):>10,.2f}  ref: {t.get('referencia')}")
    else:
        print("  ❌ Error leyendo transacciones")
        errores += 1

    return errores == 0


# ══════════════════════════════════════════════════════════
# TEST 4b — Enriquecimiento
# ══════════════════════════════════════════════════════════

def test_enriquecimiento():
    print("\n" + "═"*55)
    print("  TEST 4b — Enriquecimiento de transacciones")
    print("═"*55)

    from supabase_client import (
        insertar_transaccion,
        existe_referencia,
        enriquecer_transaccion,
        obtener_por_referencia,
    )
    from datetime import datetime

    errores = 0
    REF_TEST = "TEST-ENRICH-001"

    # Limpiar por si quedó de una prueba anterior
    try:
        from supabase_client import _cliente
        _cliente.table("transacciones").delete().eq("referencia", REF_TEST).execute()
    except:
        pass

    # 1 — Insertar transacción base sin concepto ni telefono
    print("\n  1. Insertar transacción base (sin concepto)...")
    base = {
        "email_id":   f"test-enrich-base",
        "fecha":      datetime.now().isoformat(),
        "tipo":       "salida",
        "subtipo":    "enviado",
        "monto_bs":   100.0,
        "referencia": REF_TEST,
        "comision_bs": 2.0,
        "mes_corte":  datetime.now().strftime("%Y-%m"),
    }
    ok = insertar_transaccion(base)
    if ok:
        print("  ✅ Base insertada")
    else:
        print("  ❌ Error insertando base")
        errores += 1
        return errores == 0

    # 2 — Verificar que existe
    print("\n  2. Verificar que existe por referencia...")
    if existe_referencia(REF_TEST):
        print("  ✅ Referencia encontrada")
    else:
        print("  ❌ No se encontró la referencia")
        errores += 1

    # 3 — Enriquecer con concepto y telefono
    print("\n  3. Enriquecer con concepto y telefono_destino...")
    datos_nuevos = {
        "concepto":         "Pago de prueba",
        "telefono_destino": "04121234567",
    }
    enriquecido = enriquecer_transaccion(REF_TEST, datos_nuevos)
    if enriquecido:
        print("  ✅ Enriquecimiento OK")
    else:
        print("  ❌ No se enriqueció")
        errores += 1

    # 4 — Verificar que los campos se actualizaron
    print("\n  4. Verificar campos actualizados...")
    actualizada = obtener_por_referencia(REF_TEST)
    if actualizada:
        concepto = actualizada.get("concepto")
        telefono = actualizada.get("telefono_destino")
        if concepto == "Pago de prueba" and telefono == "04121234567":
            print(f"  ✅ concepto='{concepto}' | telefono='{telefono}'")
        else:
            print(f"  ❌ Valores incorrectos: concepto='{concepto}' telefono='{telefono}'")
            errores += 1
    else:
        print("  ❌ No se pudo leer la transacción actualizada")
        errores += 1

    # 5 — Intentar enriquecer con datos que ya existen (debe ignorar)
    print("\n  5. Intentar enriquecer con datos ya existentes (debe ignorar)...")
    enriquecido2 = enriquecer_transaccion(REF_TEST, {"concepto": "Otro concepto"})
    if not enriquecido2:
        print("  ✅ Ignorado correctamente — no sobreescribe datos existentes")
    else:
        print("  ❌ Sobreescribió datos que ya existían")
        errores += 1

    # Limpiar registro de prueba
    try:
        _cliente.table("transacciones").delete().eq("referencia", REF_TEST).execute()
        print("\n  🧹 Registro de prueba eliminado")
    except:
        pass

    return errores == 0

# ══════════════════════════════════════════════════════════
# TEST 5 — Gmail (solo verifica autenticación)
# ══════════════════════════════════════════════════════════
def test_gmail():
    print("\n" + "═"*55)
    print("  TEST 5 — Gmail (autenticación)")
    print("═"*55)
    print("  ⚠️  Este test abrirá el navegador la primera vez")
    print("      para autorizar acceso a tu cuenta de Google.")

    respuesta = input("\n  ¿Continuar? (s/n): ").strip().lower()
    if respuesta != "s":
        print("  ⏭️  Test omitido")
        return True

    from gmail_reader import obtener_correos_no_leidos

    try:
        correos = obtener_correos_no_leidos()
        print(f"  ✅ Gmail conectado — correos no leídos con etiqueta BVC: {len(correos)}")
        for c in correos[:3]:
            print(f"     • {c['asunto'][:60]}")
        return True
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


# ══════════════════════════════════════════════════════════
# RUNNER
# ══════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("\n╔══════════════════════════════════════════════════════╗")
    print("║           BankTrack — Suite de Tests                ║")
    print("╚══════════════════════════════════════════════════════╝")

    tests = [
        ("Parser",          test_parser),
        ("Comisiones",      test_comisiones),
        ("DolarAPI",        test_dolar_api),
        ("Supabase",        test_supabase),
        ("Enriquecimiento", test_enriquecimiento),
        ("Gmail",           test_gmail),
    ]

    resultados = {}
    for nombre, fn in tests:
        try:
            resultados[nombre] = fn()
        except Exception as e:
            print(f"\n  💥 Error inesperado en {nombre}: {e}")
            resultados[nombre] = False

    # Resumen final
    print("\n" + "═"*55)
    print("  RESUMEN")
    print("═"*55)
    todos_ok = True
    for nombre, ok in resultados.items():
        estado = "✅ PASÓ" if ok else "❌ FALLÓ"
        print(f"  {estado}  —  {nombre}")
        if not ok:
            todos_ok = False

    print()
    if todos_ok:
        print("  🎉 Todo listo — puedes correr main.py")
    else:
        print("  ⚠️  Revisa los tests fallidos antes de correr main.py")
    print()