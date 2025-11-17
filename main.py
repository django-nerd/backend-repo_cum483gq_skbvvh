import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Product as ProductSchema

app = FastAPI(title="Street Art Fashion API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ProductCreate(BaseModel):
    title: str = Field(..., description="Product title")
    description: Optional[str] = Field(None, description="Product description")
    price: float = Field(..., ge=0, description="Price in dollars")
    category: str = Field("streetwear", description="Product category")
    in_stock: bool = Field(True, description="Whether product is in stock")
    image: Optional[str] = Field(None, description="Image URL")
    colors: Optional[List[str]] = Field(default_factory=list, description="Accent colors")


class ProductOut(ProductCreate):
    id: str


@app.get("/")
def read_root():
    return {"message": "Street Art Fashion API running"}


@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}


@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"

    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    import os as _os
    response["database_url"] = "✅ Set" if _os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if _os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


# Utility: convert Mongo document to API-friendly dict

def serialize_product(doc: dict) -> ProductOut:
    return ProductOut(
        id=str(doc.get("_id")),
        title=doc.get("title", ""),
        description=doc.get("description"),
        price=float(doc.get("price", 0)),
        category=doc.get("category", "streetwear"),
        in_stock=bool(doc.get("in_stock", True)),
        image=doc.get("image"),
        colors=doc.get("colors") or [],
    )


# Seed a few products if collection is empty

def ensure_seed_products():
    if db is None:
        return
    coll = db["product"]
    if coll.count_documents({}) == 0:
        seed_items = [
            {
                "title": "Neon Graffiti Hoodie",
                "description": "Oversized hoodie splashed with neon tags and glow ink.",
                "price": 89.0,
                "category": "hoodies",
                "in_stock": True,
                "image": "https://images.unsplash.com/photo-1512436991641-6745cdb1723f?q=80&w=1600&auto=format&fit=crop",
                "colors": ["#7C3AED", "#06B6D4", "#F59E0B"],
            },
            {
                "title": "Street Halo Sneakers",
                "description": "Chunky sneakers with iridescent spray gradients.",
                "price": 129.0,
                "category": "sneakers",
                "in_stock": True,
                "image": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?q=80&w=1600&auto=format&fit=crop",
                "colors": ["#22D3EE", "#A78BFA", "#F472B6"],
            },
            {
                "title": "Stickerbomb Cargo Pants",
                "description": "Tactical cargos with removable sticker patches.",
                "price": 74.0,
                "category": "pants",
                "in_stock": True,
                "image": "https://images.unsplash.com/photo-1520975922284-5420f8d7c44a?q=80&w=1600&auto=format&fit=crop",
                "colors": ["#10B981", "#F43F5E", "#60A5FA"],
            },
            {
                "title": "Drip Aura Cap",
                "description": "6-panel cap with melting chrome embroidery.",
                "price": 39.0,
                "category": "hats",
                "in_stock": True,
                "image": "https://images.unsplash.com/photo-1517702145080-e0f9a3fd0c49?q=80&w=1600&auto=format&fit=crop",
                "colors": ["#FB7185", "#34D399", "#818CF8"],
            },
        ]
        for item in seed_items:
            create_document("product", item)


@app.get("/api/products", response_model=List[ProductOut])
def list_products(limit: Optional[int] = 20):
    ensure_seed_products()
    try:
        docs = get_documents("product", {}, limit=limit or 20)
        return [serialize_product(d) for d in docs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/products", response_model=ProductOut)
def create_product(payload: ProductCreate):
    try:
        # Validate with schema (ensures collection exists conceptually)
        _ = ProductSchema(
            title=payload.title,
            description=payload.description,
            price=payload.price,
            category=payload.category,
            in_stock=payload.in_stock,
        )
        new_id = create_document("product", payload.model_dump())
        doc = db["product"].find_one({"_id": ObjectId(new_id)})
        return serialize_product(doc)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
