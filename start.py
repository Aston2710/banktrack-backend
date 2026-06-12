import threading
import uvicorn
import os

from api import app

def iniciar_worker():
    try:
        from main import main
        main()
    except Exception as e:
        print(f"[worker] Error en worker: {e}")

def iniciar_api():
    port = int(os.getenv("PORT", 8000))
    print(f"[api] ── Arrancando BankTrack API ──────────────────")
    print(f"[api]   PORT env var : {os.getenv('PORT', '(no seteada, usando default 8000)')}")
    print(f"[api]   Binding en   : 0.0.0.0:{port}")
    print(f"[api]   Health check : http://0.0.0.0:{port}/health")
    print(f"[api] ─────────────────────────────────────────────")
    uvicorn.run(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    print(f"[start] Iniciando BankTrack Backend...")
    hilo_worker = threading.Thread(target=iniciar_worker, daemon=True)
    hilo_worker.start()
    print(f"[start] Worker Gmail iniciado en hilo secundario")

    iniciar_api()