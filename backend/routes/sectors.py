# Market Research\routes\sectors.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from database_setup import _exec_sql  # adjust path if your db.py is in a different location

router = APIRouter(prefix="/api/sectors", tags=["Sectors"])

# -------------------------
# Pydantic models
# -------------------------
class SectorIn(BaseModel):
    sector_name: str = Field(..., min_length=2, max_length=100)

class CategoryIn(BaseModel):
    category_name: str = Field(..., min_length=2, max_length=150)

class CategoryOut(BaseModel):
    category_id: int
    category_name: str

class SectorOut(BaseModel):
    sector_id: int
    sector_name: str

# -------------------------
# Helpers
# -------------------------
def _get_sector_id(sector_name: str) -> Optional[int]:
    rows = _exec_sql(
        "SELECT sector_id FROM sectors WHERE sector_name=%s",
        (sector_name,),
        fetch=True,
    )
    return rows[0]["sector_id"] if rows else None

def _ensure_sector(sector_name: str) -> int:
    sid = _get_sector_id(sector_name)
    if sid:
        return sid
    _exec_sql(
        "INSERT INTO sectors (sector_name) VALUES (%s) "
        "ON DUPLICATE KEY UPDATE sector_name=VALUES(sector_name)",
        (sector_name,),
    )
    sid = _get_sector_id(sector_name)
    if not sid:
        raise HTTPException(status_code=500, detail="Failed to create sector")
    return sid

# -------------------------
# Routes
# -------------------------

@router.get("", response_model=List[SectorOut])
def list_sectors():
    return _exec_sql(
        "SELECT sector_id, sector_name FROM sectors ORDER BY sector_name",
        fetch=True,
    )

@router.post("", response_model=SectorOut)
def add_sector(payload: SectorIn):
    _exec_sql(
        """
        INSERT INTO sectors (sector_name)
        VALUES (%s)
        ON DUPLICATE KEY UPDATE sector_name=VALUES(sector_name)
        """,
        (payload.sector_name,),
    )
    sid = _ensure_sector(payload.sector_name)
    return {"sector_id": sid, "sector_name": payload.sector_name}

@router.get("/{sector_name}/categories", response_model=List[CategoryOut])
def list_categories_by_sector(sector_name: str):
    return _exec_sql(
        """
        SELECT c.category_id, c.category_name
        FROM product_categories c
        JOIN sectors s ON s.sector_id = c.sector_id
        WHERE s.sector_name=%s
        ORDER BY c.category_name
        """,
        (sector_name,),
        fetch=True,
    )

@router.post("/{sector_name}/categories", response_model=CategoryOut)
def add_category_to_sector(sector_name: str, payload: CategoryIn):
    sector_id = _ensure_sector(sector_name)
    _exec_sql(
        """
        INSERT INTO product_categories (sector_id, category_name)
        VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE category_name=VALUES(category_name)
        """,
        (sector_id, payload.category_name),
    )
    row = _exec_sql(
        """
        SELECT category_id, category_name
        FROM product_categories
        WHERE sector_id=%s AND category_name=%s
        """,
        (sector_id, payload.category_name),
        fetch=True,
    )
    if not row:
        raise HTTPException(status_code=500, detail="Failed to upsert category")
    return row[0]
