from fastapi import APIRouter, HTTPException, status
from datetime import datetime

from app.models.tv import PairRequest, ConcurrentPairResponse, TVListResponse, ValidationResponse, GenericScriptRequest, GenericScriptResponse
from typing import Union
from app.services.tv_service import TVService

router = APIRouter(prefix="/tv", tags=["TV Operations"])


@router.get("/list", response_model=TVListResponse)
async def list_tvs():
    """Get list of all available TVs with their pairing status"""
    try:
        return TVService.get_available_tvs()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve TV list: {str(e)}"
        )


@router.get("/{tv_id}")
async def get_tv(tv_id: str):
    """Get specific TV information"""
    tv = TVService.get_tv_by_id(tv_id)
    if not tv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"TV with ID '{tv_id}' not found"
        )
    return tv


@router.post("/pair", response_model=ConcurrentPairResponse)
async def pair_tvs(request: PairRequest):
    """Pair with one or more Samsung TVs concurrently"""
    
    # The PairRequest model validates:
    # - TV IDs list is not empty
    # - Max 10 TVs
    # - No duplicates
    # - No empty TV IDs
    # - Accepts both single TV ID and multiple TV IDs
    
    # Perform concurrent pairing
    result = TVService.concurrent_pair_tvs(request.tv_ids)
    
    # Always return 200 with detailed results
    # Individual failures are in the response body
    return result


@router.post("/validate")
async def validate_tv_ids(request: PairRequest):
    """Validate one or more TV IDs"""
    
    results = []
    for tv_id in request.tv_ids:
        validation = TVService.validate_tv_exists(tv_id)
        results.append(validation)
    
    # Summary
    valid_count = sum(1 for r in results if r.exists)
    total_count = len(results)
    
    return {
        "validations": results,
        "summary": f"{valid_count}/{total_count} TV IDs are valid",
        "all_valid": valid_count == total_count
    }


@router.post("/execute", response_model=GenericScriptResponse)
async def execute_script_generic(request: GenericScriptRequest):
    """Execute any script from the /scripts/ folder on one or more TVs
    
    Examples:
    - POST /execute with {"script_name": "power_status", "tv_ids": ["m2_tv"]}
    - POST /execute with {"script_name": "control_tv", "tv_ids": ["m2_tv"], "args": ["KEY_POWER"]}
    - POST /execute with {"script_name": "pair_tv", "tv_ids": ["m2_tv", "b4_tv"], "concurrent": true}
    """
    
    # Validate script_name is provided
    if not request.script_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="script_name is required"
        )
    
    # Execute the script
    result = TVService.execute_script(
        script_name=request.script_name,
        tv_ids=request.tv_ids,
        args=request.args,
        concurrent=request.concurrent
    )
    
    # Check if script was found
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result["error"]
        )
    
    return GenericScriptResponse(**result)


@router.post("/execute/{script_name}", response_model=GenericScriptResponse)
async def execute_script_named(script_name: str, request: GenericScriptRequest):
    """Execute a specific script from the /scripts/ folder on one or more TVs
    
    Examples:
    - POST /execute/power_status with {"tv_ids": ["m2_tv"]}
    - POST /execute/control_tv with {"tv_ids": ["m2_tv"], "args": ["KEY_POWER"]}
    - POST /execute/pair_tv with {"tv_ids": ["m2_tv", "b4_tv"], "concurrent": true}
    """
    
    # Execute the script (override script_name from URL)
    result = TVService.execute_script(
        script_name=script_name,
        tv_ids=request.tv_ids,
        args=request.args,
        concurrent=request.concurrent
    )
    
    # Check if script was found
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result["error"]
        )
    
    return GenericScriptResponse(**result)