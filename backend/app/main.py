from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import medicines, providers, benefits, insurance, calculator, search

app = FastAPI(
    title="CareCompare API",
    description="Healthcare cost transparency platform",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(medicines.router, prefix="/api/v1/medicines", tags=["medicines"])
app.include_router(providers.router, prefix="/api/v1/providers", tags=["providers"])
app.include_router(benefits.router, prefix="/api/v1/benefits", tags=["benefits"])
app.include_router(insurance.router, prefix="/api/v1/insurance", tags=["insurance"])
app.include_router(calculator.router, prefix="/api/v1/calculator", tags=["calculator"])
app.include_router(search.router, prefix="/api/v1/search", tags=["search"])


@app.get("/")
async def health_check():
    return {"status": "healthy", "app": "CareCompare API"}
