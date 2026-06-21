import json

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse, PlainTextResponse

from app.api.dependencies import BusinessContext, get_business_context_demo
from app.schemas.inventory import (
    IngredientCreate,
    IngredientResponse,
    IngredientUpdate,
    SupplierTrackerResponse,
)
from app.services.exports import export_inventory
from app.services.inventory import (
    create_ingredient,
    delete_ingredient,
    get_reorder_alerts,
    list_ingredients,
    list_suppliers,
    update_ingredient,
)


router = APIRouter()


@router.get("/inventory/reorder", response_model=list[IngredientResponse])
def reorder_alerts_route(ctx: BusinessContext = Depends(get_business_context_demo)) -> list[dict]:
    return get_reorder_alerts(ctx.business_id)


@router.post("/inventory/ingredients", response_model=IngredientResponse, status_code=status.HTTP_201_CREATED)
def create_ingredient_route(payload: IngredientCreate, ctx: BusinessContext = Depends(get_business_context_demo)) -> dict:
    if payload.business_id is not None and payload.business_id != ctx.business_id:
        raise HTTPException(status_code=403, detail="Business access denied")
    data = payload.model_dump()
    data["business_id"] = ctx.business_id
    return create_ingredient(data)


@router.get("/inventory/ingredients", response_model=list[IngredientResponse])
def list_ingredients_route(ctx: BusinessContext = Depends(get_business_context_demo)) -> list[dict]:
    return list_ingredients(ctx.business_id)


@router.get("/inventory/suppliers", response_model=SupplierTrackerResponse)
def supplier_tracker_route(ctx: BusinessContext = Depends(get_business_context_demo)) -> dict:
    return {"suppliers": list_suppliers(ctx.business_id)}


@router.get("/inventory/export")
def export_inventory_route(
    format: str = Query(default="csv"),
    ctx: BusinessContext = Depends(get_business_context_demo),
):
    export_format = format.lower()
    if export_format not in {"csv", "json"}:
        raise HTTPException(status_code=422, detail="format must be csv or json")
    content = export_inventory(ctx.business_id, export_format)
    if export_format == "json":
        return JSONResponse(content=json.loads(content))
    return PlainTextResponse(content=content, media_type="text/csv")


@router.patch("/inventory/ingredients/{ingredient_id}", response_model=IngredientResponse)
def update_ingredient_route(
    ingredient_id: int,
    payload: IngredientUpdate,
    ctx: BusinessContext = Depends(get_business_context_demo),
) -> dict:
    row = update_ingredient(ingredient_id, payload.model_dump(exclude_unset=True), ctx.business_id)
    if not row:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    return row


@router.delete("/inventory/ingredients/{ingredient_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ingredient_route(
    ingredient_id: int,
    ctx: BusinessContext = Depends(get_business_context_demo),
) -> None:
    deleted = delete_ingredient(ingredient_id, ctx.business_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Ingredient not found")
