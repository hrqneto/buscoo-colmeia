import logging
import os

# Define se é ambiente de produção ou desenvolvimento
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")  # default: development

logger = logging.getLogger("buscaflex")

# Configurações diferentes para dev e prod
if ENVIRONMENT == "production":
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
else:
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
    )
