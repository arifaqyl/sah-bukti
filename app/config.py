import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "kedai_ops.sqlite3"
DEFAULT_SUPPLIER_BANK_ACCOUNT = os.getenv("KEDAIOPS_SUPPLIER_BANK_ACCOUNT", "")
APP_BASE_URL = os.getenv("KEDAIOPS_APP_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
KEDAIOPS_BRAND_NAME = os.getenv("KEDAIOPS_BRAND_NAME", "KedaiOps")
TELEGRAM_BOT_TOKEN = os.getenv("KEDAIOPS_TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("KEDAIOPS_TELEGRAM_CHAT_ID", "")
KEDAIOPS_WEBHOOK_SECRET = os.getenv("KEDAIOPS_WEBHOOK_SECRET", "")

PAYMENT_PROVIDER = os.getenv("KEDAIOPS_PAYMENT_PROVIDER", "mock")
MOCK_PAYMENT_BASE_URL = os.getenv("KEDAIOPS_MOCK_PAYMENT_BASE_URL", APP_BASE_URL)
MOCK_PAYMENT_PREFIX = os.getenv("KEDAIOPS_MOCK_PAYMENT_PREFIX", "/pay.html?id=")

BILLPLZ_API_KEY = os.getenv("BILLPLZ_API_KEY", "")
BILLPLZ_COLLECTION_ID = os.getenv("BILLPLZ_COLLECTION_ID", "")
BILLPLZ_BASE_URL = os.getenv("BILLPLZ_BASE_URL", "https://www.billplz-sandbox.com/api/v3").rstrip("/")
BILLPLZ_CALLBACK_PATH = os.getenv("BILLPLZ_CALLBACK_PATH", "/api/payments/billplz-webhook")
BILLPLZ_REDIRECT_PATH = os.getenv("BILLPLZ_REDIRECT_PATH", "/pay.html")

# Uploads directory for receipt screenshots
UPLOADS_DIR = DATA_DIR / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)

def _read_vault_secret(*labels: str) -> str:
    vault_secrets_path = Path("D:/MyVault/SECRETS.md")
    if not vault_secrets_path.exists():
        return ""
    try:
        content = vault_secrets_path.read_text(encoding="utf-8")
    except Exception:
        return ""
    for line in content.splitlines():
        for label in labels:
            if label in line:
                return line.split(label, 1)[1].strip()
    return ""


# Resolve AI API keys from env first, then vault fallback.
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or _read_vault_secret(
    "Claude key:",
    "Anthropic key:",
    "Claude API key:",
    "Anthropic API key:",
)
CLAUDE_MODEL = os.getenv("KEDAIOPS_CLAUDE_MODEL", "claude-sonnet-4-5")
RECEIPT_AI_PROVIDER = os.getenv("KEDAIOPS_RECEIPT_AI_PROVIDER", "gemini").lower()
RECEIPT_AI_BASE_URL = os.getenv("KEDAIOPS_RECEIPT_AI_BASE_URL", "").rstrip("/")
RECEIPT_AI_API_KEY = os.getenv("KEDAIOPS_RECEIPT_AI_API_KEY", "")
RECEIPT_AI_MODEL = os.getenv("KEDAIOPS_RECEIPT_AI_MODEL", "claude-sonnet-4-6")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or _read_vault_secret("Gemini key:", "Gemini API key:")
GEMINI_FLASH_MODEL = os.getenv("KEDAIOPS_GEMINI_FLASH_MODEL", "gemini-2.5-flash")
GEMINI_TIMEOUT_SECONDS = float(os.getenv("KEDAIOPS_GEMINI_TIMEOUT_SECONDS", "12"))

WHATSAPP_PROVIDER = os.getenv("KEDE_WHATSAPP_PROVIDER", "webjs").lower()
WHATSAPP_BRIDGE_URL = os.getenv("KEDE_WHATSAPP_BRIDGE_URL", "http://127.0.0.1:3010").rstrip("/")
WHATSAPP_SESSION_NAME = os.getenv("KEDE_WHATSAPP_SESSION_NAME", "kede")
