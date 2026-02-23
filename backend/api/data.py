from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from pydantic import BaseModel
from backend.core.data import DataManager
from backend.core.store import MetadataStore
import shutil
import os
import uuid
import asyncio
from typing import List

router = APIRouter()

data_manager = DataManager()
metadata_store = MetadataStore()

class UrlImportRequest(BaseModel):
    url: str
    symbol: str
    timeframe: str

@router.post("/upload")
async def upload_dataset(
    file: UploadFile = File(...),
    symbol: str = Form(...),
    timeframe: str = Form(...)
):
    try:
        # Save to temporary file
        temp_filename = f"temp_{uuid.uuid4()}.csv"
        with open(temp_filename, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        try:
            # Process via DataManager (blocking, but fast for small files, maybe wrap if huge)
            loop = asyncio.get_running_loop()
            metadata = await loop.run_in_executor(None, data_manager.process_upload, temp_filename, symbol, timeframe)
            
            # Store Metadata
            metadata_store.add_dataset(metadata)
            
            return {"status": "success", "data": metadata}
            
        finally:
            # Cleanup temp file
            if os.path.exists(temp_filename):
                os.remove(temp_filename)
                
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/url")
async def import_from_url(request: UrlImportRequest):
    """
    Import dataset from a direct download URL (CSV or ZIP).
    """
    try:
        # Offload to thread pool to avoid blocking event loop
        loop = asyncio.get_running_loop()
        metadata = await loop.run_in_executor(
            None,
            data_manager.process_url,
            request.url,
            request.symbol,
            request.timeframe
        )

        metadata_store.add_dataset(metadata)
        return {"status": "success", "data": metadata}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Log error for debugging
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")

@router.get("/")
async def list_datasets():
    return metadata_store.list_datasets()

@router.delete("/{dataset_id}")
async def delete_dataset(dataset_id: str):
    # Get metadata to find file path
    dataset = metadata_store.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
        
    # Delete Parquet file
    file_path = dataset['file_path']
    if os.path.exists(file_path):
        os.remove(file_path)
        
    # Delete Metadata
    metadata_store.delete_dataset(dataset_id)
    
    return {"status": "deleted", "id": dataset_id}

@router.get("/{dataset_id}/discrepancies")
async def get_discrepancies(dataset_id: str):
    dataset = metadata_store.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
        
    try:
        discrepancies = data_manager.scan_discrepancies(dataset['file_path'], dataset.get('detected_tf_sec', 0))
        return {"status": "success", "discrepancies": discrepancies}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{dataset_id}/window/{index}")
async def get_dataset_window(dataset_id: str, index: int):
    dataset = metadata_store.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
        
    try:
        window_data = data_manager.get_dataset_window(dataset['file_path'], index)
        return {"status": "success", "data": window_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class RowUpdateRequest(BaseModel):
    open: float
    high: float
    low: float
    close: float
    volume: float

@router.put("/{dataset_id}/row/{index}")
async def update_dataset_row(dataset_id: str, index: int, request: RowUpdateRequest):
    dataset = metadata_store.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
        
    try:
        updates = request.dict()
        data_manager.update_dataset_row(dataset['file_path'], index, updates)
        return {"status": "success", "message": "Row updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{dataset_id}/row/{index}")
async def delete_dataset_row(dataset_id: str, index: int):
    dataset = metadata_store.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
        
    try:
        data_manager.delete_dataset_row(dataset['file_path'], index)
        return {"status": "success", "message": "Row deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{dataset_id}/interpolate/{index}")
async def interpolate_dataset_gap(dataset_id: str, index: int):
    dataset = metadata_store.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
        
    try:
        inserted = data_manager.interpolate_dataset_gap(dataset['file_path'], index, dataset.get('detected_tf_sec', 0))
        return {"status": "success", "message": f"Successfully interpolated {inserted} missing rows."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{dataset_id}/autofix/{index}")
async def autofix_dataset_row(dataset_id: str, index: int):
    dataset = metadata_store.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
        
    try:
        data_manager.autofix_dataset_row(dataset['file_path'], index)
        return {"status": "success", "message": "Row logic automatically fixed."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{dataset_id}/inspect")
async def inspect_dataset_row(dataset_id: str, query: str):
    """Inspect a specific dataset row by integer index or datetime string."""
    dataset = metadata_store.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
        
    try:
        result = data_manager.inspect_dataset_row(dataset['file_path'], query)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
