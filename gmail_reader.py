import os
import json
import base64
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from config import GMAIL_CREDENTIALS_PATH, GMAIL_TOKEN_PATH, GMAIL_LABEL

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]


def _autenticar() -> object:
    # Si las credenciales vienen como variable de entorno, escribirlas al disco
    creds_json = os.getenv("GMAIL_CREDENTIALS_JSON")
    token_json  = os.getenv("GMAIL_TOKEN_JSON")

    if creds_json and not os.path.exists(GMAIL_CREDENTIALS_PATH):
        os.makedirs(os.path.dirname(GMAIL_CREDENTIALS_PATH), exist_ok=True)
        with open(GMAIL_CREDENTIALS_PATH, "w") as f:
            json.dump(json.loads(creds_json), f)

    if token_json and not os.path.exists(GMAIL_TOKEN_PATH):
        os.makedirs(os.path.dirname(GMAIL_TOKEN_PATH), exist_ok=True)
        with open(GMAIL_TOKEN_PATH, "w") as f:
            json.dump(json.loads(token_json), f)

    creds = None
    if os.path.exists(GMAIL_TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(GMAIL_TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(GMAIL_TOKEN_PATH, "w") as token:
                token.write(creds.to_json())
        else:
            raise Exception(
                "Token inválido o expirado. Regenera el token localmente "
                "y actualiza GMAIL_TOKEN_JSON en Railway."
            )

    return build("gmail", "v1", credentials=creds)


def _decodificar_cuerpo(mensaje: dict) -> str:
    """Extrae el texto plano del cuerpo del correo."""
    cuerpo = ""
    payload = mensaje.get("payload", {})

    def extraer_partes(partes):
        texto = ""
        for parte in partes:
            mime = parte.get("mimeType", "")
            if mime == "text/plain":
                data = parte.get("body", {}).get("data", "")
                if data:
                    texto += base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
            elif "parts" in parte:
                texto += extraer_partes(parte["parts"])
        return texto

    if "parts" in payload:
        cuerpo = extraer_partes(payload["parts"])
    else:
        data = payload.get("body", {}).get("data", "")
        if data:
            cuerpo = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")

    return cuerpo


def obtener_correos_no_leidos() -> list:
    servicio = _autenticar()
    correos  = []

    try:
        # Buscar hilos (no mensajes) con la etiqueta BVC no leídos
        resultado = servicio.users().threads().list(
            userId="me",
            labelIds=[GMAIL_LABEL],
            q="is:unread"
        ).execute()

        hilos = resultado.get("threads", [])
        print(f"[gmail] Hilos no leídos encontrados: {len(hilos)}")

        for hilo in hilos:
            # Obtener todos los mensajes del hilo
            detalle_hilo = servicio.users().threads().get(
                userId="me",
                id=hilo["id"],
                format="full"
            ).execute()

            mensajes = detalle_hilo.get("messages", [])

            for mensaje in mensajes:
                # Solo procesar mensajes no leídos
                etiquetas = mensaje.get("labelIds", [])
                if "UNREAD" not in etiquetas:
                    continue

                headers = mensaje.get("payload", {}).get("headers", [])
                asunto  = next((h["value"] for h in headers if h["name"] == "Subject"), "")
                cuerpo  = _decodificar_cuerpo(mensaje)

                correos.append({
                    "id":     mensaje["id"],
                    "asunto": asunto,
                    "cuerpo": cuerpo,
                })

        print(f"[gmail] Mensajes no leídos totales: {len(correos)}")

    except Exception as e:
        print(f"[gmail] Error obteniendo correos: {e}")

    return correos

def marcar_como_leido(email_id: str):
    """Marca el correo como leído para no procesarlo de nuevo."""
    servicio = _autenticar()
    try:
        servicio.users().messages().modify(
            userId="me",
            id=email_id,
            body={"removeLabelIds": ["UNREAD"]}
        ).execute()
        print(f"[gmail] Marcado como leído: {email_id}")
    except Exception as e:
        print(f"[gmail] Error marcando como leído {email_id}: {e}")