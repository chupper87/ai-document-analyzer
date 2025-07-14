from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from config.database import engine, Base, get_db
from models.user import User
from schemas.user import UserCreate, UserResponse
from utils.auth import hash_password


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


@app.post("/users/", response_model=UserResponse)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """
    Create a new user account.

    - **username**: Username for the account
    - **email**: Valid email address
    - **password**: Password (will be hashed)
    """

    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    # Hash password
    password_hash = hash_password(user.password)

    # Create user
    db_user = User(
        username=user.username, email=user.email, password_hash=password_hash
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user
