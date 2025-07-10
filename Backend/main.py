from typing import Union
from fastapi import FastAPI
from config.database import engine
from config.settings import settings


app = FastAPI()


@app.get("/")
def read_root():
    return {"message": "AI Document Analyzer API", "status": "running"}


@app.get("/test-db")
def test_db():
    try:
        # Test connection
        connection = engine.connect()
        connection.close()
        return "Status: Database connected successfully"
    except Exception as e:
        return {"Status": "Database connection failed", "error": str(e)}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}
