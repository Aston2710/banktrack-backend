from dotenv import load_dotenv
import os

load_dotenv()

SUPABASE_URL              = os.getenv("SUPABASE_URL")
SUPABASE_KEY              = os.getenv("SUPABASE_KEY")
GMAIL_CREDENTIALS_PATH    = os.getenv("GMAIL_CREDENTIALS_PATH")
GMAIL_TOKEN_PATH          = os.getenv("GMAIL_TOKEN_PATH")
GMAIL_LABEL               = os.getenv("GMAIL_LABEL", "BVC")
DOLAR_API_URL             = os.getenv("DOLAR_API_URL")
INTERVALO_MINUTOS         = int(os.getenv("INTERVALO_MINUTOS", "5"))

# Validación al arrancar
def validar_config():
    requeridos = {
        "SUPABASE_URL":           SUPABASE_URL,
        "SUPABASE_KEY":           SUPABASE_KEY,
        "GMAIL_CREDENTIALS_PATH": GMAIL_CREDENTIALS_PATH,
        "GMAIL_TOKEN_PATH":       GMAIL_TOKEN_PATH,
        "DOLAR_API_URL":          DOLAR_API_URL,
    }
    faltantes = [k for k, v in requeridos.items() if not v]
    if faltantes:
        raise ValueError(f"Faltan variables de entorno: {', '.join(faltantes)}")