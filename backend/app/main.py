"""Punto de entrada de la API FastAPI.

En la Fase 0 solo expone un endpoint de salud para verificar el stack.
"""

from fastapi import FastAPI

app = FastAPI(title="PM Web API", version="0.1.0")


@app.get("/api/v1/health")
def health() -> dict[str, str]:
    """Indica que la API está en ejecución."""
    return {"status": "ok"}
