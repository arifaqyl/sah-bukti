from pydantic import BaseModel, ConfigDict, Field


class CustomerCreate(BaseModel):
    business_id: int | None = Field(default=None, ge=1)
    name: str = Field(min_length=1, max_length=120)
    phone: str | None = Field(default=None, max_length=40)
    email: str | None = Field(default=None, max_length=120)


class CustomerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    phone: str | None = Field(default=None, max_length=40)
    email: str | None = Field(default=None, max_length=120)


class CustomerResponse(CustomerCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: str
