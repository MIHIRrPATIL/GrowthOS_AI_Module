"""
Central runtime configuration, read once from the environment (and a local
.env file if present — real environment variables always win).
"""
import logging
import os
import secrets

from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger("growthos.config")

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+psycopg2://growthos:growthos_dev_pw@localhost:5432/growthos_loyalty",
)

# --- JWT (short-lived access tokens minted from an API key) ---------------
JWT_ISSUER = "growthos-loyalty"
JWT_ALGORITHM = "HS256"
JWT_TTL_SECONDS = int(os.environ.get("JWT_TTL_SECONDS", "900"))
JWT_SECRET = os.environ.get("JWT_SECRET")
if not JWT_SECRET:
    # No insecure hard-coded default. An ephemeral secret means tokens simply
    # stop validating after a restart — fine for dev, loud enough to notice.
    JWT_SECRET = secrets.token_urlsafe(48)
    log.warning("JWT_SECRET is not set; using an ephemeral secret (tokens die on restart).")

# --- Platform administration (creating tenants) ---------------------------
# Disabled unless explicitly configured. Never reuse a tenant key for this.
PLATFORM_ADMIN_KEY = os.environ.get("PLATFORM_ADMIN_KEY") or None

# --- CORS -----------------------------------------------------------------
CORS_ORIGINS = [o.strip() for o in os.environ.get("CORS_ORIGINS", "*").split(",") if o.strip()]
