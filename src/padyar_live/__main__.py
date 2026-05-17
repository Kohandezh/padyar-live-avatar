from __future__ import annotations

import logging
import signal

import uvicorn

from padyar_live.api.app import create_app
from padyar_live.runtime.config import RuntimeConfig

logger = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    config = RuntimeConfig()
    app = create_app(config)

    server = uvicorn.Server(
        uvicorn.Config(
            app,
            host=config.host,
            port=config.port,
            log_level="info",
        )
    )

    def handle_shutdown(signum: int, frame: object) -> None:
        logger.info("Received signal %s — initiating graceful shutdown", signum)
        server.should_exit = True

    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    server.run()


if __name__ == "__main__":
    main()
