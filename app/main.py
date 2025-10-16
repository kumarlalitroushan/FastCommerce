from argon2 import hash_password
from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
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


# Default role: CUSTOMER
@app.post("/register", response_model= UserResponse)
async def register_user(user: UserCreate, db: db_dependency):

    #checking if user already exists
    db_user = db.query(Users).filter(
        (Users.email == user.email) | (Users.username == user.username)
    ).first()

    # raising HTTPException if user already exists
    if db_user:
        raise HTTPException(
            status_code=400,
            detail="Email or username already registered"
        )
    
    # create a new user
    db_user = Users(
        email=user.email,
        username=user.username,
        hashed_password= pwd_context.hash(user.password),
        full_name=user.full_name,
        role = UserRole.CUSTOMER
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user

# user login
@app.post("/token", response_model=Token)
async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: db_dependency):

    # Authenticate user
    user = db.query(Users).filter(Users.username == form_data.username).first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, 
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

# -------- Product Management Endpoints ------------

@app.post("/products", response_model= ProductResponse)
async def create_product(product: ProductCreate, db: db_dependency, current_user: Users= Depends(get_admin_user)):
    db_product = Product(**product.dict())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    
    return db_product
