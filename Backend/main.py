# Standard library imports
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import UUID
import uuid

# Third-party imports
from fastapi import FastAPI, Depends, HTTPException, status, File, UploadFile
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import aiofiles

# Local application imports
from config.database import engine, Base, get_db
from models.user import User
from models.category import Category
from models.document import Document
from schemas.user import UserCreate, UserResponse, UserUpdate
from schemas.category import CategoryCreate, CategoryResponse, CategoryUpdate
from schemas.document import DocumentCreate, DocumentResponse
from schemas.token import Token
from utils.auth import (
    hash_password,
    authenticate_user,
    create_access_token,
    get_current_user,
)

# Configuration
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


# Application lifespan management
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


# Create FastAPI instance
app = FastAPI(
    title="AI Document Analyzer API",
    description="API for document upload and AI analysis",
    version="1.0.0",
    lifespan=lifespan,
)

# =====================================================
# Health Check Endpoints
# =====================================================


@app.get("/")
def read_root():
    return {"message": "AI Document Analyzer API", "status": "running"}


@app.get("/test-db")
def test_db():
    try:
        connection = engine.connect()
        connection.close()
        return {"status": "Database connection OK"}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Database connection failed: {str(e)}"
        )


# =====================================================
# Authentication Endpoints
# =====================================================


@app.post("/users/", response_model=UserResponse)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """
    Create a new user account.

    - **username**: Username for the account
    - **email**: Valid email address
    - **password**: Password (will be hashed)
    """
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    # Create new user with hashed password
    db_user = User(
        username=user.username,
        email=user.email,
        password_hash=hash_password(user.password),
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user


@app.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    """Authenticate user and return access token."""
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}


# =====================================================
# User Profile Endpoints
# =====================================================


@app.get("/users/me", response_model=UserResponse)
def read_users_me(current_user: User = Depends(get_current_user)):
    """Get current authenticated user information."""
    return current_user


@app.put("/users/me", response_model=UserResponse)
def update_user_me(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update current user's profile information."""
    # Check username availability
    if user_update.username is not None:
        existing_user = (
            db.query(User)
            .filter(User.username == user_update.username)
            .filter(User.id != current_user.id)
            .first()
        )
        if existing_user:
            raise HTTPException(status_code=400, detail="Username already taken")
        current_user.username = user_update.username

    # Check email availability
    if user_update.email is not None:
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


# =====================================================
# Category Management Endpoints
# =====================================================


@app.post("/categories/", response_model=CategoryResponse)
def create_category(
    category: CategoryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new category for the current user."""
    # Check if category name already exists for this user
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


@app.get("/categories/", response_model=list[CategoryResponse])
def read_categories(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get all categories for the current user."""
    categories = (
        db.query(Category)
        .filter(Category.user_id == current_user.id, Category.deleted_at.is_(None))
        .all()
    )
    return categories


@app.put("/categories/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: UUID,
    category_update: CategoryUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a category for the current user."""
    # Find category
    category = (
        db.query(Category)
        .filter(
            Category.id == category_id,
            Category.user_id == current_user.id,
            Category.deleted_at.is_(None),
        )
        .first()
    )

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
        )

    # Check if new name is available
    if category_update.name is not None and category_update.name != category.name:
        existing_category = (
            db.query(Category)
            .filter(
                Category.user_id == current_user.id,
                Category.name == category_update.name,
                Category.deleted_at.is_(None),
                Category.id != category_id,
            )
            .first()
        )

        if existing_category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category with this name already exists",
            )

        category.name = category_update.name

    # Update color if provided
    if category_update.color is not None:
        category.color = category_update.color

    db.commit()
    db.refresh(category)

    return category


@app.delete("/categories/{category_id}")
def delete_category(
    category_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Soft delete a category for the current user."""
    category = (
        db.query(Category)
        .filter(
            Category.id == category_id,
            Category.user_id == current_user.id,
            Category.deleted_at.is_(None),
        )
        .first()
    )

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
        )

    # Soft delete - set deleted_at timestamp
    category.deleted_at = datetime.now(timezone.utc)
    db.commit()

    return {"message": "Category deleted successfully"}


# =====================================================
# Document Management Endpoints
# =====================================================


@app.post("/documents/", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    category_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Upload a document for analysis.

    - **file**: The document file (PDF, DOCX, TXT)
    - **category_id**: Optional category to assign the document to
    """
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    # Generate unique file ID and get extension
    file_id = uuid.uuid4()
    file_extension = Path(file.filename).suffix

    # Create user-specific folder structure
    user_folder = UPLOAD_DIR / str(current_user.id)
    user_folder.mkdir(exist_ok=True)

    file_path = user_folder / f"{file_id}{file_extension}"

    # Save file asynchronously
    try:
        async with aiofiles.open(file_path, "wb") as f:
            content = await file.read()
            await f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not save file: {str(e)}")

    # Create database entry
    db_document = Document(
        user_id=current_user.id,
        category_id=category_id,
        original_filename=file.filename,
        file_path=str(file_path),
        file_size=len(content),
        mime_type=file.content_type or "application/octet-stream",
        status="pending",
    )

    db.add(db_document)
    db.commit()
    db.refresh(db_document)

    return db_document
