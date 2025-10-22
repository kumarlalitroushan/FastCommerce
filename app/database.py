from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from sqlalchemy.ext.declarative import declarative_base
from dotenv import load_dotenv

# using env variables to setup db connection string
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

#SQLAlchemy engine
engine = create_engine(
    DATABASE_URL,
    pool_size=20,        
    max_overflow=30,   
    echo=False           
)

#session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()



