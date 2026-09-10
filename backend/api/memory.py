from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import memory.database as db
from auth.dependencies import get_current_user, verify_csrf_header

router = APIRouter()

class MemoryItem(BaseModel):
    id: str
    content: str
    category: str
    enabled: bool
    created_at: str

class CreateMemoryRequest(BaseModel):
    content: str
    category: Optional[str] = "general"

class UpdateMemoryRequest(BaseModel):
    content: Optional[str] = None
    category: Optional[str] = None

class SetMemoryEnabledRequest(BaseModel):
    enabled: bool

@router.get("/memory", response_model=List[MemoryItem])
async def get_memories(category: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    try:
        return db.get_all_memories(current_user["id"], category=category)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/memory", response_model=MemoryItem, dependencies=[Depends(verify_csrf_header)])
async def add_memory(request: CreateMemoryRequest, current_user: dict = Depends(get_current_user)):
    if not request.content.strip():
        raise HTTPException(status_code=400, detail="Content cannot be empty")
    try:
        return db.add_memory(current_user["id"], content=request.content.strip(), category=request.category or "general")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/memory/{memory_id}", response_model=MemoryItem, dependencies=[Depends(verify_csrf_header)])
async def update_memory(memory_id: str, request: UpdateMemoryRequest, current_user: dict = Depends(get_current_user)):
    if request.content is not None and not request.content.strip():
        raise HTTPException(status_code=400, detail="Content cannot be empty")
    updated = db.update_memory(
        memory_id,
        current_user["id"],
        content=request.content.strip() if request.content is not None else None,
        category=request.category,
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="Memory item not found")
    return updated

@router.patch("/memory/{memory_id}/enabled", response_model=MemoryItem, dependencies=[Depends(verify_csrf_header)])
async def set_memory_enabled(memory_id: str, request: SetMemoryEnabledRequest, current_user: dict = Depends(get_current_user)):
    updated = db.set_memory_enabled(memory_id, current_user["id"], request.enabled)
    if updated is None:
        raise HTTPException(status_code=404, detail="Memory item not found")
    return updated

@router.delete("/memory/{memory_id}", dependencies=[Depends(verify_csrf_header)])
async def delete_memory(memory_id: str, current_user: dict = Depends(get_current_user)):
    success = db.delete_memory(memory_id, current_user["id"])
    if not success:
        raise HTTPException(status_code=404, detail="Memory item not found")
    return {"status": "deleted", "id": memory_id}
