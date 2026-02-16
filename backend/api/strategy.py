from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from backend.core.strategy import StrategyLoader
from typing import List, Optional

router = APIRouter()
loader = StrategyLoader()

class StrategyCreate(BaseModel):
    name: str
    code: str

class StrategyResponse(BaseModel):
    name: str
    versions: List[int]
    latest_version: int

@router.get("", response_model=List[StrategyResponse])
@router.get("/", response_model=List[StrategyResponse])
async def list_strategies():
    strategies = loader.list_strategies()
    return strategies

@router.post("/")
async def save_strategy(strategy: StrategyCreate):
    try:
        version = loader.save_strategy(strategy.name, strategy.code)
        return {"status": "saved", "name": strategy.name, "version": version}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/validate")
async def validate_strategy(strategy: StrategyCreate):
    """
    Validate strategy code without saving.
    """
    result = loader.validate_strategy_code(strategy.code)
    return result

@router.get("/{name}/versions")
async def get_strategy_versions(name: str):
    versions = loader._get_versions(name) # helper access
    if not versions:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return {"name": name, "versions": versions}

@router.get("/{name}/{version}")
async def get_strategy_code(name: str, version: int):
    code = loader.get_strategy_code(name, version)
    if code is None:
        raise HTTPException(status_code=404, detail="Strategy version not found")
    return {"name": name, "version": version, "code": code}

@router.delete("/{name}")
async def delete_strategy(name: str):
    try:
        loader.delete_strategy(name)
        return {"status": "deleted", "name": name}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Strategy not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/templates/list")
async def list_templates():
    """
    List available strategy templates.
    """
    import os
    templates_dir = "strategies/_templates"
    if not os.path.exists(templates_dir):
        return []
    
    templates = []
    for f in os.listdir(templates_dir):
        if f.endswith(".py"):
            templates.append(f.replace(".py", ""))
    return templates

@router.get("/templates/{name}")
async def get_template(name: str):
    """
    Get code for a specific template.
    """
    import os
    filepath = f"strategies/_templates/{name}.py"
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Template not found")
    
    with open(filepath, "r") as f:
        code = f.read()
    return {"name": name, "code": code}
