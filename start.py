import threading
import uvicorn
import os

# Pre-importar el app antes de lanzar hilos evita race conditions
# en el sistema de importación de módulos de Python
from api import app

def iniciar_worker():
    try:
        from main import main
        main()
    except Exception as e:
        print(f"[worker] Error en worker: {e}")

def iniciar_api():
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    hilo_worker = threading.Thread(target=iniciar_worker, daemon=True)
    hilo_worker.start()

    iniciar_api()