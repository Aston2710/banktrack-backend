import threading
import uvicorn
import os

def iniciar_worker():
    from main import main
    main()

def iniciar_api():
    uvicorn.run("api:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)))

if __name__ == "__main__":
    # Worker en hilo secundario
    hilo_worker = threading.Thread(target=iniciar_worker, daemon=True)
    hilo_worker.start()

    # API en el hilo principal — Railway necesita que el proceso web
    # esté en el hilo principal para detectar que está escuchando
    iniciar_api()