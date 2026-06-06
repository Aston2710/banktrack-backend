import schedule
import time
from datetime import datetime

from config import validar_config, INTERVALO_MINUTOS
from gmail_reader import obtener_correos_no_leidos, marcar_como_leido
from parser import parsear_correo
from comisiones import resolver_comision
from dolar_api import obtener_tasa_bcv
from supabase_client import insertar_transaccion, existe_referencia
from alertas import verificar_limite_mes_actual


def procesar_correos():
    print(f"\n[main] ─── Ciclo: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} ───")

    # 1. Obtener tasa del dólar una sola vez por ciclo
    tasa = obtener_tasa_bcv()
    if tasa:
        print(f"[main] Tasa BCV: Bs. {tasa}")
    else:
        print("[main] No se pudo obtener tasa — se guardará sin conversión USD")

    # 2. Obtener correos no leídos con etiqueta BVC
    correos = obtener_correos_no_leidos()
    if not correos:
        print("[main] Sin correos nuevos")
        return

    # 3. Procesar cada correo
    insertados = 0
    for correo in correos:
        datos = parsear_correo(correo["asunto"], correo["cuerpo"])

        if datos.get("subtipo") == "desconocido":
            print(f"[main] Correo no reconocido: {correo['asunto'][:60]}")
            marcar_como_leido(correo["id"])
            continue

        # 4. Calcular comisión
        comision = resolver_comision(datos)

        # Monto real — rechazados no mueven dinero
        monto_real = datos.get("monto_bs")
        if datos.get("subtipo") == "rechazado":
            monto_real = 0.0

        # 5. Calcular equivalente en USD
        monto_usd = None
        if tasa and monto_real and monto_real > 0:
            monto_usd = round(monto_real / tasa, 4)

        # 6. Armar registro para Supabase
        mes_corte = datos["fecha"].strftime("%Y-%m") if datos.get("fecha") else datetime.now().strftime("%Y-%m")

        registro = {
            "email_id":              correo["id"],
            "fecha":                 datos["fecha"].isoformat() if datos.get("fecha") else datetime.now().isoformat(),
            "tipo":                  datos["tipo"],
            "subtipo":               datos["subtipo"],
            "monto_bs":              monto_real,
            "tasa_dolar":            tasa,
            "monto_usd":             monto_usd,
            "referencia":            datos.get("referencia"),
            "celular_origen":        datos.get("celular_origen"),
            "celular_destino":       datos.get("celular_destino"),
            "telefono_destino":      datos.get("telefono_destino"),
            "banco_destino":         datos.get("banco_destino"),
            "beneficiario":          datos.get("beneficiario"),
            "comision_bs":           comision,
            "comision_declarada_bs": datos.get("comision_declarada_bs"),
            "mes_corte":             mes_corte,
            "concepto":              datos.get("concepto"),
        }

        # 7. Verificar duplicado por referencia
        referencia = datos.get("referencia")
        if referencia and existe_referencia(referencia):
            print(f"[main] Referencia duplicada: {referencia} — ignorado")
            marcar_como_leido(correo["id"])
            continue

        # 8. Insertar en Supabase
        if insertar_transaccion(registro):
            insertados += 1

        # 9. Marcar correo como leído (procesado)
        marcar_como_leido(correo["id"])

    print(f"[main] Procesados: {len(correos)} correos — Insertados: {insertados}")

    # 10. Verificar límite de gasto
    verificar_limite_mes_actual()


def main():
    print("╔══════════════════════════════════════╗")
    print("║         BankTrack Backend            ║")
    print("╚══════════════════════════════════════╝")

    # Validar que el .env está completo
    validar_config()
    print("[main] Configuración válida ✅")

    # Primer ciclo inmediato al arrancar
    procesar_correos()

    # Luego cada N minutos
    schedule.every(INTERVALO_MINUTOS).minutes.do(procesar_correos)
    print(f"[main] Corriendo cada {INTERVALO_MINUTOS} minutos. Ctrl+C para detener.\n")

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()