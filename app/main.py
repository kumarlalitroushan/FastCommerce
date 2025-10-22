from argon2 import hash_password
from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, TypeAlias
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
db_dependency : TypeAlias = Annotated[Session, Depends(get_db)]


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

@app.put("/admin/users/{user_id}/role", response_model=UserResponse)
async def update_user_role(user_id: int, role_update: UserRoleUpdate, db: db_dependency, current_user: Users=Depends(get_super_admin_user)):
    user = db.query(Users).filter(Users.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # prevent superusers to demote themselves
    if user.id == current_user.id and role_update.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=400,
            detail="Cannot demote yourself from SUPER_ADMIN"
        )

    user.role = role_update.role

    db.commit()
    db.refresh(user) 

    return user

# -------- Product Management Endpoints ------------


# add products (Note: only admin/super admin can add products)
@app.post("/products", response_model= ProductResponse)
async def create_product(product: ProductCreate, db: db_dependency, current_user: Users= Depends(get_admin_user)):
    db_product = Product(**product.dict())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    
    return db_product

# Get product details with skip and limit feature
@app.get("/products", response_model= List[ProductResponse])
async def get_products(
    db: db_dependency,
    skip: int= 0,
    limit: int = 10,
    category: Optional[str] = None,
):
    query = db.query(Product).filter(Product.is_active == True)
    products = query.offset(skip).limit(limit).all()

    return products

@app.get("/products/{product_id}", response_model=ProductResponse)
async def get_product(db: db_dependency, product_id:int):
    product = db.query(Product).filter(Product.id == product_id).first()

    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="product not found")

    return product


# ============================================================================
# 11. ORDER MANAGEMENT ENDPOINTS
# ============================================================================

@app.post("/orders", response_model= OrderResponse)
async def create_order(order: OrderCreate, db: db_dependency, current_user : Users= Depends(get_current_user)):
    total_amount = 0
    order_items_data = []

    # Validating products and calculate total

    for item in order.items:
        product = db.query(Product).filter(Product.id == item.product_id).first()

        if not product:
            raise HTTPException(
                status_code=404, 
                detail=f"Product {item.product_id} not found"
            )
        
        if product.stock_quantity < item.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock for product {product.name}"
            )
        
        item_total = product.price * item.quantity
        total_amount += item_total

        order_items_data.append({
            "product_id": item.product_id,
            "quantity": item.quantity,
            "price_per_item": product.price,
            "product": product
        })

    # Saving order in DB
    db_order = Order(
        user_id=current_user.id,
        total_amount=total_amount,
        status="pending",
        stripe_payment_intent_id= 'pass'
    )

    db.add(db_order)
    db.commit()
    db.refresh(db_order)

    # Create order Items

    for items in order_items_data:
        db_order_item = OrderItem(
            order_id = db_order.id,
            product_id = items["product_id"],
            quantity=items["quantity"],
            price_per_item=items["price_per_item"]
        )
        db.add(db_order_item)

    db.commit()

    return db_order

# get all orders
@app.get("/orders", response_model= List[OrderResponse])
async def get_user_orders(db: db_dependency, current_user: Users= Depends(get_current_user)):
    orders = db.query(Order).filter(current_user.id == Order.user_id).all()

    return orders

# get particular order
@app.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: int,
    db: db_dependency,
    current_user: Users = Depends(get_current_user)
):
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.user_id == current_user.id
    ).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return order