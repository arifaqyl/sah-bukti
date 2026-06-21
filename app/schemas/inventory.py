from pydantic import BaseModel, ConfigDict, Field


class IngredientCreate(BaseModel):
    business_id: int | None = Field(default=None, ge=1)
    name: str = Field(min_length=1, max_length=120)
    unit: str = Field(default="pcs", min_length=1, max_length=30)
    current_stock: float = Field(default=0, ge=0)
    reorder_point: float = Field(default=0, ge=0)
    supplier: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=500)


class IngredientUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    unit: str | None = Field(default=None, min_length=1, max_length=30)
    current_stock: float | None = Field(default=None, ge=0)
    reorder_point: float | None = Field(default=None, ge=0)
    supplier: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=500)


class IngredientResponse(IngredientCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    last_updated: str


class StockUpdateRequest(BaseModel):
    quantity: float = Field(ge=0)


class SupplierIngredientSummary(BaseModel):
    id: int
    name: str
    current_stock: float
    reorder_point: float
    unit: str
    supplier: str | None = None
    notes: str | None = None


class SupplierGroupResponse(BaseModel):
    supplier: str
    ingredient_count: int
    low_stock_count: int
    ingredients: list[SupplierIngredientSummary]


class SupplierTrackerResponse(BaseModel):
    suppliers: list[SupplierGroupResponse]
