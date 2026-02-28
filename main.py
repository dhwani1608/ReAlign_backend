"""Main FastAPI application"""

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import os
from datetime import datetime
from database import init_db
from security import RateLimitMiddleware, SecurityHeadersMiddleware

# Import routers
from routers import auth, designer, site

# Initialize database
init_db()

# Create FastAPI app
app = FastAPI(
    title="ReAlign AI - Backend API",
    description="API for reconciling design assumptions with on-site construction reality",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# CORS middleware - restrict to specific origins in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        # Add production domain here
        # "https://yourdomain.com",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],  # Restrict to needed methods
    allow_headers=["*"],
)

# Security middleware - add BEFORE CORS
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)

generated_layouts_dir = os.path.join(os.path.dirname(__file__), "generated_layouts")
os.makedirs(generated_layouts_dir, exist_ok=True)
app.mount("/generated-layouts", StaticFiles(directory=generated_layouts_dir), name="generated-layouts")


# ===== Root Endpoint =====
@app.get("/")
async def root():
    """API health check"""
    return {
        "status": "healthy",
        "application": "AI-Driven Generative Design & Autonomous Construction System",
        "version": "1.0.0",
        "endpoints": {
            "docs": "/docs",
            "redoc": "/redoc",
            "auth": "/auth",
            "designer": "/designer",
            "site": "/site"
        }
    }


# ===== Include Routers =====
app.include_router(auth.router)
app.include_router(designer.router)
app.include_router(site.router)


# ===== Health Check =====
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "operational",
        "timestamp": datetime.now().isoformat()
    }


# ===== Global Exception Handler =====
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "detail": exc.detail,
            "status_code": exc.status_code
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
