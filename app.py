import logging

import uvicorn

from musicapi.config import get_settings
from musicapi.routes import app


def main() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    uvicorn.run(
        "musicapi.routes:app",
        host=settings.app_host,
        port=settings.runtime_port,
        reload=settings.debug,
    )


if __name__ == "__main__":
    main()
