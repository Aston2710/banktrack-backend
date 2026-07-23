import re
from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY
from datetime import datetime
from typing import Optional

_cliente: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# Columnas nuevas que pueden no existir aún en la BD.
# Si Supabase las rechaza, se reintenta sin ellas para no perder la transacción.
_COLUMNAS_OPCIONALES = ["tasa_euro", "monto_eur"]


def _es_error_columna_faltante(mensaje: str) -> bool:
    m = mensaje.lower()
    return "pgrst204" in m or ("column" in m and ("does not exist" in m or "could not find" in m))


def _solo_digitos(valor: Optional[str]) -> str:
    return re.sub(r"\D", "", valor or "")


def _es_enmascarado(valor: Optional[str]) -> bool:
    """Un contacto enmascarado trae asteriscos, ej. '****-*****35'."""
    return bool(valor) and "*" in valor


def _mismos_ultimos_2(a: Optional[str], b: Optional[str]) -> bool:
    """True si ambos terminan en los mismos 2 dígitos (misma cuenta/celular)."""
    da, db = _solo_digitos(a), _solo_digitos(b)
    return len(da) >= 2 and len(db) >= 2 and da[-2:] == db[-2:]


def _fmt(valor) -> str:
    """Valor legible para el log; '—' si está vacío."""
    return "—" if valor in (None, "") else str(valor)


def _resumen(datos: dict) -> str:
    """Resumen consistente con los valores clave de una transacción."""
    partes = [
        f"Bs. {_fmt(datos.get('monto_bs'))}",
        f"USD {_fmt(datos.get('monto_usd'))}",
        f"EUR {_fmt(datos.get('monto_eur'))}",
        f"concepto: {_fmt(datos.get('concepto'))}",
    ]
    return " | ".join(partes)


def insertar_transaccion(datos: dict) -> bool:
    try:
        _cliente.table("transacciones").insert(datos).execute()
        print(f"[supabase] ✅ Insertada: {datos.get('subtipo')} | "
              f"ref: {datos.get('referencia')} | {_resumen(datos)}")
        return True
    except Exception as e:
        mensaje = str(e)
        if "duplicate" in mensaje.lower() or "unique" in mensaje.lower():
            print(f"[supabase] ⚠️  Ya existe email_id: {datos.get('email_id')} — ignorado")
            return False
        if _es_error_columna_faltante(mensaje):
            reducido = {k: v for k, v in datos.items() if k not in _COLUMNAS_OPCIONALES}
            print("[supabase] ⚠️  Columnas EUR no existen en la BD — reintentando sin ellas. "
                  "Ejecuta el SQL de md/base-de-datos.md para habilitarlas.")
            try:
                _cliente.table("transacciones").insert(reducido).execute()
                print(f"[supabase] ✅ Insertada (sin EUR): ref: {datos.get('referencia')} | {_resumen(reducido)}")
                return True
            except Exception as e2:
                print(f"[supabase] ❌ Error insertando (reintento): {e2}")
                return False
        print(f"[supabase] ❌ Error insertando: {e}")
        return False


def existe_referencia(referencia: str) -> bool:
    if not referencia:
        return False
    try:
        res = (_cliente.table("transacciones")
               .select("id")
               .eq("referencia", referencia)
               .execute())
        return len(res.data) > 0
    except Exception as e:
        print(f"[supabase] Error verificando referencia: {e}")
        return False


def obtener_por_referencia(referencia: str) -> Optional[dict]:
    """Retorna la transacción existente con esa referencia."""
    try:
        res = (_cliente.table("transacciones")
               .select("*")
               .eq("referencia", referencia)
               .limit(1)
               .execute())
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"[supabase] Error obteniendo por referencia: {e}")
        return None


def enriquecer_transaccion(referencia: str, datos_nuevos: dict) -> bool:
    """
    Compara campos vacíos en la transacción existente con los datos nuevos.
    Solo actualiza campos que estaban vacíos y ahora tienen valor.
    Loguea exactamente qué campos se actualizaron.
    """
    existente = obtener_por_referencia(referencia)
    if not existente:
        return False

    campos_a_actualizar = {}

    # Campos candidatos a enriquecimiento
    candidatos = [
        "concepto",
        "fecha",
        "contacto_destino",
        "banco_destino",
        "comercio",
        "tarjeta_ultimos",
        "etiquetas",
        "celular_origen",
        "beneficiario",
        # Monto y conversiones. monto_usd / monto_eur / tasa_dolar / tasa_euro
        # llegan con valor SOLO cuando el correo es de hoy (main.py calcula la
        # tasa del día únicamente en ese caso); en otra fecha llegan None y se
        # saltan por el `if valor_nuevo` de abajo. Así el rellenado de la
        # conversión ocurre solo a la fecha de hoy.
        "monto_bs",
        "tasa_dolar",
        "monto_usd",
        "tasa_euro",
        "monto_eur",
    ]

    for campo in candidatos:
        valor_nuevo    = datos_nuevos.get(campo)
        valor_existente = existente.get(campo)

        # Solo actualizar si el nuevo tiene valor y el existente está vacío
        if valor_nuevo and not valor_existente:
            campos_a_actualizar[campo] = valor_nuevo

    # contacto_destino: si el registro existente tiene el número ENMASCARADO
    # (ej. '****-*****35', del correo "enviado") y el correo nuevo trae el
    # número COMPLETO (ej. '04129823335', del "pago inmediato"), lo mejoramos
    # al completo — pero solo si coinciden los últimos 2 dígitos, confirmando
    # que es la misma cuenta/celular.
    nuevo_contacto     = datos_nuevos.get("contacto_destino")
    contacto_existente = existente.get("contacto_destino")
    if (nuevo_contacto
            and _es_enmascarado(contacto_existente)
            and not _es_enmascarado(nuevo_contacto)
            and _mismos_ultimos_2(nuevo_contacto, contacto_existente)):
        campos_a_actualizar["contacto_destino"] = nuevo_contacto

    if not campos_a_actualizar:
        print(f"[supabase] ⏭️  Duplicado sin datos nuevos: ref {referencia} — ignorado | {_resumen(existente)}")
        return False

    try:
        _cliente.table("transacciones") \
            .update(campos_a_actualizar) \
            .eq("referencia", referencia) \
            .execute()

        cambios_str = ", ".join(
            f"{campo}: {_fmt(existente.get(campo))} → {_fmt(valor)}"
            for campo, valor in campos_a_actualizar.items()
        )
        print(f"[supabase] 🔄 Enriquecida ref {referencia}: {cambios_str}")
        return True
    except Exception as e:
        mensaje = str(e)
        if _es_error_columna_faltante(mensaje):
            reducido = {k: v for k, v in campos_a_actualizar.items()
                        if k not in _COLUMNAS_OPCIONALES}
            if not reducido:
                print(f"[supabase] ⏭️  Solo había columnas EUR (inexistentes) para enriquecer ref {referencia} — ignorado")
                return False
            print("[supabase] ⚠️  Columnas EUR no existen en la BD — enriqueciendo sin ellas. "
                  "Ejecuta el SQL de md/base-de-datos.md para habilitarlas.")
            try:
                _cliente.table("transacciones") \
                    .update(reducido) \
                    .eq("referencia", referencia) \
                    .execute()
                cambios_str = ", ".join(
                    f"{campo}: {_fmt(existente.get(campo))} → {_fmt(valor)}"
                    for campo, valor in reducido.items()
                )
                print(f"[supabase] 🔄 Enriquecida (sin EUR) ref {referencia}: {cambios_str}")
                return True
            except Exception as e2:
                print(f"[supabase] Error enriqueciendo (reintento): {e2}")
                return False
        print(f"[supabase] Error enriqueciendo: {e}")
        return False


def obtener_transacciones_mes(mes: str) -> list:
    try:
        res = (_cliente.table("transacciones")
               .select("*")
               .eq("mes_corte", mes)
               .order("fecha", desc=True)
               .execute())
        return res.data or []
    except Exception as e:
        print(f"[supabase] Error consultando mes {mes}: {e}")
        return []


def obtener_configuracion() -> dict:
    try:
        res = _cliente.table("configuracion").select("*").limit(1).execute()
        return res.data[0] if res.data else {}
    except Exception as e:
        print(f"[supabase] Error obteniendo configuración: {e}")
        return {}


def guardar_cierre_mensual(mes: str) -> bool:
    try:
        transacciones = obtener_transacciones_mes(mes)
        if not transacciones:
            print(f"[supabase] Sin transacciones para cerrar mes {mes}")
            return False

        entradas_bs  = sum(t["monto_bs"] for t in transacciones if t["tipo"] == "entrada")
        salidas_bs   = sum(t["monto_bs"] for t in transacciones if t["tipo"] == "salida")
        entradas_usd = sum(t.get("monto_usd") or 0 for t in transacciones if t["tipo"] == "entrada")
        salidas_usd  = sum(t.get("monto_usd") or 0 for t in transacciones if t["tipo"] == "salida")
        entradas_eur = sum(t.get("monto_eur") or 0 for t in transacciones if t["tipo"] == "entrada")
        salidas_eur  = sum(t.get("monto_eur") or 0 for t in transacciones if t["tipo"] == "salida")
        comisiones   = sum(t.get("comision_bs") or 0 for t in transacciones)
        tasas        = [t["tasa_dolar"] for t in transacciones if t.get("tasa_dolar")]
        tasa_prom    = round(sum(tasas) / len(tasas), 4) if tasas else None
        tasas_eur    = [t["tasa_euro"] for t in transacciones if t.get("tasa_euro")]
        tasa_prom_eur = round(sum(tasas_eur) / len(tasas_eur), 4) if tasas_eur else None
        pct_comision = round((comisiones / salidas_bs * 100), 4) if salidas_bs > 0 else 0

        cierre = {
            "mes":                   mes,
            "total_entradas_bs":     round(entradas_bs, 2),
            "total_salidas_bs":      round(salidas_bs, 2),
            "total_entradas_usd":    round(entradas_usd, 4),
            "total_salidas_usd":     round(salidas_usd, 4),
            "total_entradas_eur":    round(entradas_eur, 4),
            "total_salidas_eur":     round(salidas_eur, 4),
            "total_comisiones_bs":   round(comisiones, 2),
            "porcentaje_comisiones": pct_comision,
            "tasa_promedio_mes":     tasa_prom,
            "tasa_promedio_eur_mes": tasa_prom_eur,
            "cerrado_en":            datetime.utcnow().isoformat(),
        }

        try:
            _cliente.table("cierres_mensuales").upsert(cierre).execute()
        except Exception as e:
            if not _es_error_columna_faltante(str(e)):
                raise
            reducido = {k: v for k, v in cierre.items()
                        if k not in ("total_entradas_eur", "total_salidas_eur", "tasa_promedio_eur_mes")}
            print("[supabase] ⚠️  Columnas EUR no existen en cierres_mensuales — guardando sin ellas. "
                  "Ejecuta el SQL de md/base-de-datos.md.")
            _cliente.table("cierres_mensuales").upsert(reducido).execute()
        print(f"[supabase] Cierre mensual guardado: {mes}")
        return True
    except Exception as e:
        print(f"[supabase] Error guardando cierre: {e}")
        return False