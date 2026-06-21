import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "kedai_ops.sqlite3"
DEFAULT_SUPPLIER_BANK_ACCOUNT = os.getenv("SAHBUKTI_SUPPLIER_BANK_ACCOUNT", "")
APP_BASE_URL = os.getenv("SAHBUKTI_APP_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
SAHBUKTI_BRAND_NAME = os.getenv("SAHBUKTI_BRAND_NAME", "Sah.Bukti")
DEFAULT_OWNER_WHATSAPP = os.getenv("SAHBUKTI_DEFAULT_OWNER_WHATSAPP", "")
TELEGRAM_BOT_TOKEN = os.getenv("SAHBUKTI_TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("SAHBUKTI_TELEGRAM_CHAT_ID", "")
SAHBUKTI_WEBHOOK_SECRET = os.getenv("SAHBUKTI_WEBHOOK_SECRET", "")

PAYMENT_PROVIDER = os.getenv("SAHBUKTI_PAYMENT_PROVIDER", "mock")
MOCK_PAYMENT_BASE_URL = os.getenv("SAHBUKTI_MOCK_PAYMENT_BASE_URL", APP_BASE_URL)
MOCK_PAYMENT_PREFIX = os.getenv("SAHBUKTI_MOCK_PAYMENT_PREFIX", "/pay.html?id=")
MANUAL_QR_DESTINATION_TEXT = os.getenv(
    "SAHBUKTI_MANUAL_QR_DESTINATION_TEXT",
    "Use your business QR or bank transfer",
)

BILLPLZ_API_KEY = os.getenv("BILLPLZ_API_KEY", "")
BILLPLZ_COLLECTION_ID = os.getenv("BILLPLZ_COLLECTION_ID", "")
BILLPLZ_BASE_URL = os.getenv("BILLPLZ_BASE_URL", "https://www.billplz-sandbox.com/api/v3").rstrip("/")
BILLPLZ_CALLBACK_PATH = os.getenv("BILLPLZ_CALLBACK_PATH", "/api/v1/payments/billplz-webhook")
BILLPLZ_REDIRECT_PATH = os.getenv("BILLPLZ_REDIRECT_PATH", "/pay.html")
BILLPLZ_X_SIGNATURE_KEY = os.getenv("BILLPLZ_X_SIGNATURE_KEY", "")

# Uploads directory for receipt screenshots
UPLOADS_DIR = DATA_DIR / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)

CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY") or os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.getenv("SAHBUKTI_CLAUDE_MODEL", "claude-sonnet-4-5")
RECEIPT_AI_PROVIDER = os.getenv("SAHBUKTI_RECEIPT_AI_PROVIDER", "gemini").lower()
RECEIPT_AI_BASE_URL = os.getenv("SAHBUKTI_RECEIPT_AI_BASE_URL", "").rstrip("/")
RECEIPT_AI_API_KEY = os.getenv("SAHBUKTI_RECEIPT_AI_API_KEY", "")
RECEIPT_AI_MODEL = os.getenv("SAHBUKTI_RECEIPT_AI_MODEL", "claude-sonnet-4-6")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_FLASH_MODEL = os.getenv("SAHBUKTI_GEMINI_FLASH_MODEL", "gemini-2.5-flash")
GEMINI_TIMEOUT_SECONDS = float(os.getenv("SAHBUKTI_GEMINI_TIMEOUT_SECONDS", "12"))

WHATSAPP_PROVIDER = os.getenv("SAHBUKTI_WHATSAPP_PROVIDER", "waha").lower()
WHATSAPP_BRIDGE_URL = os.getenv("SAHBUKTI_WHATSAPP_BRIDGE_URL", "http://127.0.0.1:3000").rstrip("/")
WHATSAPP_SESSION_NAME = os.getenv("SAHBUKTI_WHATSAPP_SESSION_NAME", "default")
WHATSAPP_API_KEY = os.getenv("SAHBUKTI_WHATSAPP_API_KEY", "")
WHATSAPP_LINK_UI_ENABLED = os.getenv("SAHBUKTI_ENABLE_WHATSAPP_LINK_UI", "0").lower() in {"1", "true", "yes", "on"}
WHATSAPP_ALLOWED_NUMBERS = tuple(
    value.strip() for value in os.getenv("SAHBUKTI_WHATSAPP_ALLOWED_NUMBERS", "").split(",") if value.strip()
)
REMINDER_PROVIDER = os.getenv("SAHBUKTI_REMINDER_PROVIDER", "mock").lower()
