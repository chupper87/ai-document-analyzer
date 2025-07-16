from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from config.database import engine, Base, get_db
from models.user import User
from schemas.user import UserCreate, UserResponse, UserUpdate
from utils.auth import hash_password
from fastapi.security import OAuth2PasswordRequestForm
from schemas.token import Token
from utils.auth import authenticate_user, create_access_token, get_current_user
from schemas.category import CategoryCreate, CategoryResponse
from models.category import Category


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 App starting up...")
    try:
        # Test database connection
        connection = engine.connect()
        connection.close()
        print("✅ Database connection OK")

        # Create tables
        Base.metadata.create_all(bind=engine)
        print("📊 Database tables created")
    except Exception as e:
        print(f"❌ Database startup failed: {e}")

    yield  # App is running

    # Shutdown
    print("👋 App shutting down...")


app = FastAPI(lifespan=lifespan)


@app.get("/")
def read_root():
    return {"message": "AI Document Analyzer API", "status": "running"}


@app.get("/test-db")
def test_db():
    try:
        connection = engine.connect()
        connection.close()
        print("✅ Database connection OK")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")


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


@app.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/users/me", response_model=UserResponse)
def read_users_me(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user information.
    """
    return current_user


@app.put("/users/me", response_model=UserResponse)
def update_user_me(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update current user's profile information.
    """

    if user_update.username is not None:
        # Check if username exists
        existing_user = (
            db.query(User)
            .filter(User.username == user_update.username)
            .filter(User.id != current_user.id)
            .first()
        )
        if existing_user:
            raise HTTPException(status_code=400, detail="Username already taken")
        current_user.username = user_update.username

    if user_update.email is not None:
        # Check if email exists
        existing_user = (
            db.query(User)
            .filter(User.email == user_update.email)
            .filter(User.id != current_user.id)
            .first()
        )
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already taken")
        current_user.email = user_update.email

    db.commit()
    db.refresh(current_user)
    return current_user


@app.post("/categories/", response_model=CategoryResponse)
def create_category(
    category: CategoryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new category for the current user.
    """

    existing_category = (
        db.query(Category)
        .filter(
            Category.user_id == current_user.id,
            Category.name == category.name,
            Category.deleted_at.is_(None),
        )
        .first()
    )

    if existing_category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category with this name already exists",
        )

    # Create new category
    db_category = Category(
        user_id=current_user.id, name=category.name, color=category.color
    )

    db.add(db_category)
    db.commit()
    db.refresh(db_category)

    return db_category
