from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
import stripe
from typing import List, Annotated

from app.models import *
from app.schemas import *
from app.database import engine, SessionLocal
from app.auth import *

# Initialize FastAPI application
app = FastAPI(
    title="E-commerce API",
    description="Advanced e-commerce API with payment processing, background tasks, and caching",
    version="1.0.0",
    docs_url="/docs",      # Swagger UI documentation
    redoc_url="/redoc"     # ReDoc documentation
)

# Create database tables
Base.metadata.create_all(bind=engine)

# method for db session handeling
def get_db():
    db = SessionLocal()
    try:
        yield db     
    finally:
        db.close()    

#dependency injection
db_dependency = Annotated[Session, Depends(get_db)]


# ---- user endpoints ----

@app.post("/register", response_model= UserResponse)
async def register_user(user: UserCreate, db: db_dependency):

    #checking if user already exists
    db_user = db.query(User).filter(
        (User.email == user.email) | (User.username == user.username)
    ).first()

    # raising HTTPException if user already exists
    if db_user:
        raise HTTPException(
            status_code=400,
            detail="Email or username already registered"
        )
    
    # create a new user
    hashed_password = get_password_hash(user.password)
    db_user = User(
        email=user.email,
        username=user.username,
        hashed_password=hashed_password,
        full_name=user.full_name
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user


