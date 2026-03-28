"""
QLM API — Charting Endpoints.
Provides metadata and resampled OHLCV bars for the frontend interactive chart.
"""
from fastapi import APIRouter, HTTPException, Query
from backend.core.store import MetadataStore
from backend.core.chart_provider import ChartDataProvider
from typing import Optional
import os
import logging

logger = logging.getLogger("QLM.API.Chart")
router = APIRouter()
metadata_store = MetadataStore()

@router.get("/{dataset_id}/meta")
async def get_chart_meta(dataset_id: str):
    """Get chart configuration metadata (valid timeframes, range) for a dataset."""
    dataset = metadata_store.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
        
    try:
        base_tf_sec = dataset.get('detected_tf_sec', 0)
        valid_tfs = ChartDataProvider.get_valid_timeframes(base_tf_sec)
        
        return {
            "status": "success",
            "meta": {
                "dataset_id": dataset['id'],
                "symbol": dataset['symbol'],
                "base_tf_sec": base_tf_sec,
                "start_date": dataset.get('start_date'),
                "end_date": dataset.get('end_date'),
                "total_rows": dataset.get('row_count', 0),
                "valid_timeframes": valid_tfs
            }
        }
    except Exception as e:
        logger.error(f"Chart Meta Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{dataset_id}/bars")
async def get_chart_bars(
    dataset_id: str, 
    tf: int = Query(60, description="Target timeframe in seconds"),
    end: Optional[int] = Query(None, description="Unix timestamp cursor (exclusive) for scroll-back"),
    limit: int = Query(2000, description="Max number of bars to return")
):
    """Get resampled OHLCV bars for the chart view."""
    dataset = metadata_store.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
        
    file_path = dataset.get('file_path')
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Dataset file missing")
        
    try:
        # Validate that the requested timeframe is valid for this dataset
        base_tf_sec = dataset.get('detected_tf_sec', 0)
        valid_tfs = ChartDataProvider.get_valid_timeframes(base_tf_sec)
        is_valid = any(t['sec'] == tf for t in valid_tfs)
        
        if not is_valid and tf > 0:
            # If not in the standard list, enforce the integer multiple rule manually
            if base_tf_sec > 0 and (tf < base_tf_sec or tf % base_tf_sec != 0):
                raise ValueError(f"Invalid timeframe {tf}s. Must be a multiple of base runtime {base_tf_sec}s.")
                
        # Limit the chunk size to prevent memory abuse
        safe_limit = min(limit, 5000)
        
        result = ChartDataProvider.get_chart_window(
            file_path=file_path,
            target_tf_sec=tf,
            end_cursor=end,
            limit=safe_limit
        )
        
        return {
            "status": "success",
            "data": result
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Chart Bars Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
