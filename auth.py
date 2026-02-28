"""Authentication and JWT token handling"""

from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import os

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 24 * 60  # 24 hours

# Password hashing
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def hash_password(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Get the current authenticated user from token"""
    credential_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        role: str = payload.get("role")
        
        if user_id is None or role is None:
            raise credential_exception
    except JWTError:
        raise credential_exception
    
    return {"user_id": int(user_id), "role": role}


async def get_design_engineer(current_user = Depends(get_current_user)):
    """Verify user is a design engineer"""
    if current_user["role"] != "design_engineer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only design engineers can access this resource"
        )
    return current_user


async def get_site_engineer(current_user = Depends(get_current_user)):
    """Verify user is a site engineer"""
    if current_user["role"] != "site_engineer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only site engineers can access this resource"
        )
    return current_user


async def get_any_user(current_user = Depends(get_current_user)):
    """Allow any authenticated user"""
    return current_user
