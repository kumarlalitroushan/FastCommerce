from pydantic import BaseModel, EmailStr, field_validator, constr
from typing import List, Optional
from datetime import datetime
from app.models import UserRole, ProductCategory

# Schema for user registration
class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: constr(min_length=8) # type: ignore
    full_name: Optional[str] = None
    
# Schema for user data in responses (no password)    
class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    full_name: Optional[str]
    is_active: bool
    role: UserRole
    created_at: datetime
    
    class Config:
        from_attributes = True 

# Admins can change the roles
class UserRoleUpdate(BaseModel):
    role: UserRole

#Schema for updating user information
class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None

# Schema for creating new products
class ProductCreate(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    stock_quantity: int = 0
    category: ProductCategory 
    
    @field_validator('price')
    def validate_price(cls, v):
        if v <= 0:
            raise ValueError('Price must be positive')
        return v

# Schema for product data in responses
class ProductResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    price: float
    stock_quantity: int
    category: Optional[str]
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# Order Schemas
class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int
    
    @field_validator('quantity')
    def validate_quantity(cls, v):
        if v <= 0:
            raise ValueError('Quantity must be positive')
        return v

class OrderCreate(BaseModel):
    items: List[OrderItemCreate]

# Schema for order items in responses
class OrderItemResponse(BaseModel):

    id: int
    product_id: int
    quantity: int
    price_per_item: float
    product: ProductResponse
    
    class Config:
        from_attributes = True

# Schema for order data in responses
class OrderResponse(BaseModel):

    id: int
    user_id: int
    total_amount: float
    status: str
    created_at: datetime
    order_items: List[OrderItemResponse]
    
    class Config:
        from_attributes = True

# Schema for token payload data
class TokenData(BaseModel):
    username: Optional[str] = None

# pydantic models to validate username and password before submitting to db
class CreateUserRequest(BaseModel):
    username : str
    password : str

class Token(BaseModel):
    access_token : str
    token_type: str