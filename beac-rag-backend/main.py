"""Point d'entree : lance l'API FastAPI.

Usage : python main.py   (ou : uvicorn src.api.app:app --reload)
"""
from __future__ import annotations

import uvicorn

from src.config import settings


def main() -> None:
    uvicorn.run(
        "src.api.app:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
    )


if __name__ == "__main__":
    main()
