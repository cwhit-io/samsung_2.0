from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.endpoints import tv

app = FastAPI(
    title="Samsung TV Controller API",
    description="API for controlling Samsung Smart TVs",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(tv.router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Samsung TV Controller API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "list_tvs": "GET /api/v1/tv/list",
            "get_tv": "GET /api/v1/tv/{tv_id}",
            "pair_tvs": "POST /api/v1/tv/pair (1+ TV IDs, concurrent)",
            "validate_tvs": "POST /api/v1/tv/validate (1+ TV IDs)",
            "execute_any_script": "POST /api/v1/tv/execute/{script_name} (generic executor)"
        },
        "examples": {
            "single_tv": {"tv_ids": ["m2_tv"]},
            "multiple_tvs": {"tv_ids": ["m2_tv", "b4_tv", "t1_tv"]},
            "script_with_args": {"tv_ids": ["m2_tv"], "args": ["KEY_POWER"], "concurrent": False}
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}