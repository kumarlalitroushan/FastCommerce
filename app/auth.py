from datetime import datetime, timedelta, timezone
from typing import List, Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, APIRouter
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import os
from sqlalchemy.orm import Session
from app.database import engine, SessionLocal
from dotenv import load_dotenv
from app.schemas import Token, CreateUserRequest
from typing import Annotated
from app.models import Users, UserRole



# Security configuration
load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password hashing
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# OAuth2 scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# router for token
router = APIRouter(
    prefix='/auth',
    tags = ['auth']
)

def get_db():
    db = SessionLocal()
    try:
        yield db     
    finally:
        db.close() 

# database dependency injection
db_dependency = Annotated[Session, Depends(get_db)]

""" ------------------------- FUNCTIONS -----------------------------------------------------------------
"""

# this will authenticate user with hashed password from database
def authenticate_user(username: str, password: str, db: db_dependency):
    user = db.query(Users).filter(Users.username == username).first()
    if not user:
        return False
    if not pwd_context.verify(password, user.hashed_password):
        return False
    return user

    """Verify a plain password against its hash"""
def verify_password(plain_password: str, hashed_password: str) -> bool:

    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db: db_dependency):
    try:
        # Decode JWT token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="wrong Token: access denied")
    
    # Get user from database
    user = db.query(Users).filter(Users.username == username).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No such user in database")
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    return user

"""
    Generic role checker - checks if user has any of the required roles
    This is a helper function, not used directly as a dependency
"""    
async def require_role(
    required_roles: List[UserRole],
    current_user: Users = Depends(get_current_user)
) -> Users:
    if current_user.role not in required_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied. Required roles: {[role.value for role in required_roles]}"
        )
    return current_user


    """
    Dependency that ensures the current user is an ADMIN or SUPER_ADMIN
    Usage: @app.get("/admin-endpoint", dependencies=[Depends(get_admin_user)])
    """ 
async def get_admin_user(current_user: Users = Depends(get_current_user)) -> Users:
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

    """
    Dependency that ensures the current user is a SUPER_ADMIN
    Usage: @app.delete("/users/{id}", dependencies=[Depends(get_super_admin_user)])
    """
async def get_super_admin_user(current_user: Users = Depends(get_current_user)) -> Users:

    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required"
        )
    return current_user


