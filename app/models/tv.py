from pydantic import BaseModel, validator
from typing import Optional, List
from datetime import datetime


class TVConfig(BaseModel):
    """TV configuration model"""
    id: str
    name: str
    host: str
    port: int
    mac_address: str


class PairRequest(BaseModel):
    """Request to pair one or more TVs"""
    tv_ids: List[str]
    
    @validator('tv_ids')
    def validate_tv_ids(cls, v):
        # Handle single string (convert to list)
        if isinstance(v, str):
            v = [v]
        
        if not v:
            raise ValueError('TV IDs list cannot be empty')
        if len(v) > 20:  # Limit to prevent abuse (increased for demo)
            raise ValueError('Cannot pair more than 20 TVs at once')
        
        # Clean and validate each ID
        cleaned_ids = []
        for tv_id in v:
            if not tv_id or not tv_id.strip():
                raise ValueError('TV ID cannot be empty')
            cleaned_ids.append(tv_id.strip())
        
        # Check for duplicates
        if len(cleaned_ids) != len(set(cleaned_ids)):
            raise ValueError('Duplicate TV IDs not allowed')
        
        return cleaned_ids
    
    # Allow both formats: {"tv_ids": ["id1", "id2"]} OR {"tv_id": "id1"}
    @validator('tv_ids', pre=True)
    def handle_single_tv_id(cls, v, values):
        # If tv_ids is not provided but tv_id is, use tv_id
        return v


class PairResponse(BaseModel):
    """Response from pairing operation"""
    status: str  # "success", "failed", "not_found"
    message: str
    tv_id: str
    tv_name: Optional[str] = None
    timestamp: datetime


class ConcurrentPairResponse(BaseModel):
    """Response from concurrent pairing operations"""
    total_requested: int
    results: List[PairResponse]
    summary: str
    execution_time_seconds: float


class GenericScriptRequest(BaseModel):
    """Generic request for any TV script"""
    script_name: Optional[str] = None  # Optional for named endpoints like /execute/{script_name}
    tv_ids: List[str]
    args: Optional[List[str]] = []
    concurrent: Optional[bool] = True
    
    @validator('tv_ids')
    def validate_tv_ids(cls, v):
        if isinstance(v, str):
            v = [v]
        if not v:
            raise ValueError('TV IDs list cannot be empty')
        if len(v) > 20:
            raise ValueError('Cannot process more than 20 TVs at once')
        return [tv_id.strip() for tv_id in v if tv_id.strip()]


class GenericScriptResponse(BaseModel):
    """Generic response from any TV script execution"""
    script_name: str
    total_requested: int
    results: List[dict]
    summary: str
    execution_time_seconds: float
    concurrent: bool


class TVStatusResponse(BaseModel):
    """Response with TV status information"""
    tv_id: str
    name: str
    host: str
    port: int
    mac_address: str
    is_paired: bool
    paired_at: Optional[str] = None


class TVListResponse(BaseModel):
    """Response with list of available TVs"""
    tvs: List[TVStatusResponse]
    count: int


class ValidationResponse(BaseModel):
    """Response for TV ID validation"""
    tv_id: str
    exists: bool
    message: str





class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str
    message: str
    timestamp: datetime
    token: str
    paired_at: str

class TVPairingRequest(BaseModel):
    tv_id: str