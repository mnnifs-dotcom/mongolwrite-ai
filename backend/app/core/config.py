from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    app_env: str = "development"
    secret_key: str = "change-me-in-production"
    frontend_origin: str = "http://localhost:3000"
    frontend_dir: str = ""
    check_max_chars: int = 100_000
    admin_username: str = "Admin write"
    admin_password: str = "Ilove@00"
    google_client_id: str = ""
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o"
    # QPay — leave empty until credentials are provided; checkout stays stub-ready.
    qpay_client_id: str = ""
    qpay_client_secret: str = ""
    qpay_invoice_code: str = ""
    qpay_base_url: str = "https://merchant.qpay.mn/v2"
    qpay_callback_url: str = ""


settings = Settings()
