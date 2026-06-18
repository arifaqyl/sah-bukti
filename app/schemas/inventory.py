from pydantic import BaseModel, ConfigDict, Field


class IngredientCreate(BaseModel):
    business_id: int = Field(default=1, ge=1)
    name: str = Field(min_length=1, max_length=120)
    unit: str = Field(default="pcs", min_length=1, max_length=30)
    current_stock: float = Field(default=0, ge=0)
    reorder_point: float = Field(default=0, ge=0)
    supplier: str | None = Field(default=None, max_length=120)


class IngredientUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    unit: str | None = Field(default=None, min_length=1, max_length=30)
    current_stock: float | None = Field(default=None, ge=0)
    reorder_point: float | None = Field(default=None, ge=0)
    supplier: str | None = Field(default=None, max_length=120)


class IngredientResponse(IngredientCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    last_updated: str


class StockUpdateRequest(BaseModel):
    quantity: float = Field(ge=0)
