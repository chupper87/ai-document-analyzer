from typing import Union
from fastapi import FastAPI
from config.database import engine, Base
from config.settings import settings
from models import user, document, category


app = FastAPI()


Base.metadata.create_all(bind=engine)  # Create all databases at start


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
