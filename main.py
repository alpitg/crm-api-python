from fastapi import FastAPI
from core.routes import setup_router
from core.cores import setup_cors

app = FastAPI(
    title="Art Show CRM API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    swagger_ui_parameters={"docExpansion": "none"}
)

# load_dotenv()
# print(load_dotenv(find_dotenv()))

# Register routes
setup_router(app)

# Register CORS middleware
setup_cors(app)


# ✅ Only for development
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)

#  For production, use:
# uvicorn app.main:app --host 0.0.0.0 --port 8000
