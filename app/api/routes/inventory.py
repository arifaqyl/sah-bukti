import json

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import JSONResponse, PlainTextResponse

from app.schemas.inventory import IngredientCreate, IngredientResponse, IngredientUpdate
from app.services.exports import export_inventory
from app.services.inventory import create_ingredient, get_reorder_alerts, list_ingredients, update_ingredient


router = APIRouter()


@router.get("/inventory/reorder", response_model=list[IngredientResponse])
def reorder_alerts_route(business_id: int = Query(default=1, ge=1)) -> list[dict]:
    return get_reorder_alerts(business_id)


@router.post("/inventory/ingredients", response_model=IngredientResponse, status_code=status.HTTP_201_CREATED)
def create_ingredient_route(payload: IngredientCreate) -> dict:
    return create_ingredient(payload.model_dump())


@router.get("/inventory/ingredients", response_model=list[IngredientResponse])
def list_ingredients_route(business_id: int = Query(default=1, ge=1)) -> list[dict]:
    return list_ingredients(business_id)


@router.get("/inventory/export")
def export_inventory_route(
    business_id: int = Query(default=1, ge=1),
    format: str = Query(default="csv"),
):
    export_format = format.lower()
    if export_format not in {"csv", "json"}:
        raise HTTPException(status_code=422, detail="format must be csv or json")
    content = export_inventory(business_id, export_format)
    if export_format == "json":
        return JSONResponse(content=json.loads(content))
    return PlainTextResponse(content=content, media_type="text/csv")


@router.patch("/inventory/ingredients/{ingredient_id}", response_model=IngredientResponse)
def update_ingredient_route(ingredient_id: int, payload: IngredientUpdate) -> dict:
    row = update_ingredient(ingredient_id, payload.model_dump(exclude_unset=True))
    if not row:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    return row
