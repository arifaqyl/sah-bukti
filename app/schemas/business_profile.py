from pydantic import BaseModel, Field, field_validator


class BusinessProfileResponse(BaseModel):
    business_id: int
    name: str
    owner_whatsapp: str | None = None
    whatsapp_group_chat_id: str | None = None
    whatsapp_group_name: str | None = None
    industry: str
    tagline: str | None = None
    theme_color: str | None = None


class BusinessProfileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    owner_whatsapp: str | None = Field(default=None, max_length=40)
    whatsapp_group_chat_id: str | None = Field(default=None, max_length=80)
    whatsapp_group_name: str | None = Field(default=None, max_length=120)
    industry: str | None = Field(default=None, min_length=1, max_length=60)
    tagline: str | None = Field(default=None, max_length=120)
    theme_color: str | None = Field(default=None, max_length=7)

    @field_validator("theme_color")
    @classmethod
    def validate_theme_color(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if len(value) != 7 or not value.startswith("#"):
            raise ValueError("theme_color must be a 6-digit hex like #D4A853")
        hex_part = value[1:]
        if any(ch not in "0123456789abcdefABCDEF" for ch in hex_part):
            raise ValueError("theme_color must be a 6-digit hex like #D4A853")
        return value.upper()
