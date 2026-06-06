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
    ]

    errores = 0
    for caso in casos:
        resultado = parsear_correo(caso["asunto"], caso["cuerpo"])
        print(f"\n  ── {caso['nombre']} ──")
        for k, v in resultado.items():
            print(f"    {k:28} → {v}")
        if resultado.get("monto_bs") is None:
            print(f"  ❌ ERROR: monto_bs no extraído")
            errores += 1
        elif resultado.get("fecha") is None:
            print(f"  ❌ ERROR: fecha no extraída")
            errores += 1
        else:
            print(f"  ✅ OK")

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
        ("Parser",     test_parser),
        ("Comisiones", test_comisiones),
        ("DolarAPI",   test_dolar_api),
        ("Supabase",   test_supabase),
        ("Gmail",      test_gmail),
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