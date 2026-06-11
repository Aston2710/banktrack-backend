import schedule
import time
from datetime import datetime

from config import validar_config, INTERVALO_MINUTOS
from gmail_reader import obtener_correos_no_leidos, marcar_como_leido
from parser import parsear_correo
from comisiones import resolver_comision
from dolar_api import obtener_tasa_bcv
from supabase_client import (
    insertar_transaccion,
    existe_referencia,
    enriquecer_transaccion,
)
from alertas import verificar_limite_mes_actual


def procesar_correos():
    print(f"\n[main] ─── Ciclo: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} ───")

    tasa = obtener_tasa_bcv()
    if tasa:
        print(f"[main] Tasa BCV: Bs. {tasa}")
    else:
        print("[main] Sin tasa disponible — se guardará sin conversión USD")

    correos = obtener_correos_no_leidos()
    if not correos:
        print("[main] Sin correos nuevos")
        return

    insertados   = 0
    enriquecidos = 0
    ignorados    = 0

    for correo in correos:
        datos = parsear_correo(correo["asunto"], correo["cuerpo"])
        subtipo    = datos.get("subtipo")
        referencia = datos.get("referencia")

        # ── Desconocido ───────────────────────────────────────────────────
        if subtipo == "desconocido":
            print(f"[main] ❓ No reconocido: {correo['asunto'][:60]}")
            marcar_como_leido(correo["id"])
            ignorados += 1
            continue

        # ── Verificar duplicado por referencia ────────────────────────────
        if referencia and existe_referencia(referencia):
            enriquecido = enriquecer_transaccion(referencia, datos)
            if enriquecido:
                enriquecidos += 1
            else:
                ignorados += 1
            marcar_como_leido(correo["id"])
            continue

        # ── Calcular monto real ───────────────────────────────────────────
        monto_real = datos.get("monto_bs")
        if subtipo == "rechazado":
            monto_real = 0.0

        monto_usd = None
        if tasa and monto_real and monto_real > 0:
            monto_usd = round(monto_real / tasa, 4)

        mes_corte = (datos["fecha"].strftime("%Y-%m")
                     if datos.get("fecha")
                     else datetime.now().strftime("%Y-%m"))

        # ── Armar registro ────────────────────────────────────────────────
        registro = {
            "email_id":              correo["id"],
            "fecha":                 datos["fecha"].isoformat() if datos.get("fecha") else datetime.now().isoformat(),
            "tipo":                  datos["tipo"],
            "subtipo":               subtipo,
            "monto_bs":              monto_real,
            "tasa_dolar":            tasa,
            "monto_usd":             monto_usd,
            "referencia":            referencia,
            "celular_origen":        datos.get("celular_origen"),
            "celular_destino":       datos.get("celular_destino"),
            "telefono_destino":      datos.get("telefono_destino"),
            "banco_destino":         datos.get("banco_destino"),
            "beneficiario":          datos.get("beneficiario"),
            "comercio":              datos.get("comercio"),
            "tarjeta_ultimos":       datos.get("tarjeta_ultimos"),
            "comision_bs":           resolver_comision(datos),
            "comision_declarada_bs": datos.get("comision_declarada_bs"),
            "mes_corte":             mes_corte,
            "concepto":              datos.get("concepto"),
            "etiquetas":             datos.get("etiquetas") or [],
        }

        if insertar_transaccion(registro):
            insertados += 1

        marcar_como_leido(correo["id"])

    print(f"\n[main] ── Resumen del ciclo ──────────────────────────")
    print(f"[main]   Procesados:   {len(correos)}")
    print(f"[main]   Insertados:   {insertados}")
    print(f"[main]   Enriquecidos: {enriquecidos}")
    print(f"[main]   Ignorados:    {ignorados}")
    print(f"[main] ─────────────────────────────────────────────────")

    verificar_limite_mes_actual()


def main():
    print("╔══════════════════════════════════════╗")
    print("║         BankTrack Backend            ║")
    print("╚══════════════════════════════════════╝")

    validar_config()
    print("[main] Configuración válida ✅")

    procesar_correos()

    schedule.every(INTERVALO_MINUTOS).minutes.do(procesar_correos)
    print(f"[main] Corriendo cada {INTERVALO_MINUTOS} minutos. Ctrl+C para detener.\n")

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()