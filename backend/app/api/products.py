"""Products API endpoints for product catalog."""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/products")


class ProductType(BaseModel):
    """A specific product type within a category."""

    id: str
    name: str
    description: str


class ProductCategory(BaseModel):
    """A product category with available types."""

    id: str
    name: str
    description: str
    types: list[ProductType]


class ProductCatalogResponse(BaseModel):
    """Complete product catalog."""

    categories: list[ProductCategory]


# Product catalog based on furniture collections in GCS
# IDs match metadata.category values used in Firestore knowledge_chunks
PRODUCT_CATALOG = [
    ProductCategory(
        id="bracken",
        name="Bracken",
        description="Bracken furniture collection",
        types=[],
    ),
    ProductCategory(
        id="calden",
        name="Calden",
        description="Calden furniture collection",
        types=[],
    ),
    ProductCategory(
        id="modero",
        name="Modero",
        description="Modero furniture collection",
        types=[],
    ),
    ProductCategory(
        id="neo",
        name="Neo",
        description="Neo furniture collection",
        types=[],
    ),
    ProductCategory(
        id="whitehaven",
        name="Whitehaven",
        description="Whitehaven furniture collection",
        types=[],
    ),
]


def get_product_details(
    product_category: str,
    product_type: str | None = None,
) -> tuple[ProductCategory | None, ProductType | None]:
    """Look up a product category and optional type from the catalog.

    Args:
        product_category: Collection ID to look up (e.g., 'bracken', 'calden').
        product_type: Optional type ID within the category.

    Returns:
        Tuple of (category, type). Both None if category not found.
        Type is None if not requested or not found within the category.
    """
    category = next((c for c in PRODUCT_CATALOG if c.id == product_category), None)
    if category is None:
        return None, None

    if product_type is None:
        return category, None

    ptype = next((t for t in category.types if t.id == product_type), None)
    return category, ptype


@router.get("", response_model=ProductCatalogResponse)
async def list_products() -> ProductCatalogResponse:
    """List all available product categories and types.

    Returns the complete product catalog that users can select from
    when creating training sessions. Product selection drives RAG
    filtering to provide relevant product knowledge during roleplay.

    Returns:
        ProductCatalogResponse: Complete catalog of product categories and types.

    Example:
        GET /api/v1/products
    """
    return ProductCatalogResponse(categories=PRODUCT_CATALOG)


@router.get("/categories", response_model=list[str])
async def list_categories() -> list[str]:
    """List all available product category IDs.

    Returns a simple list of category IDs for quick reference.

    Returns:
        List of category IDs (e.g., ["living_room", "bedroom", "mattress"]).

    Example:
        GET /api/v1/products/categories
    """
    return [category.id for category in PRODUCT_CATALOG]
