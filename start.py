import threading
import uvicorn
from main import main as iniciar_worker

def iniciar_api():
    uvicorn.run("api:app", host="0.0.0.0", port=int(__import__('os').getenv("PORT", 8000)))

if __name__ == "__main__":
    # Arrancar la API en un hilo separado
    hilo_api = threading.Thread(target=iniciar_api, daemon=True)
    hilo_api.start()

    # Arrancar el worker en el hilo principal
    iniciar_worker()