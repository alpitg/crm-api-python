from fastapi import FastAPI
from app.controllers.default import DeafultController

app = FastAPI(
    title="Art Show CRM API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Import and register master routes
DeafultController(app).register_routes()


# ✅ Only for development
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)

#  For production, use:
# uvicorn app.main:app --host 0.0.0.0 --port 8000
