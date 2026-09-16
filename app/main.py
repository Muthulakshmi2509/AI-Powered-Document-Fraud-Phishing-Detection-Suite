from fastapi import FastAPI
from app.api.document_router import router
from app.database import init_db

app = FastAPI(title="Intelligent Doc Verifier")

@app.on_event("startup")
def startup_event():
    init_db()

app.include_router(router, prefix="/api")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
