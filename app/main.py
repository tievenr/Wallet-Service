from fastapi import FastAPI
from app.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json"
)

@app.get("/health")
def health_check():
    return {"status": "healthy"}

#TO-DO: API routes