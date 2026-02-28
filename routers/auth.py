"""Authentication routes"""

from fastapi import APIRouter, HTTPException, status
from datetime import timedelta
from models import UserCreate, UserLogin, Token, UserResponse
from auth import hash_password, verify_password, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from database import UserDB
from security import check_password_strength

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse)
async def register(user: UserCreate):
    """Register a new user with strong password requirement"""
    # Validate password strength
    password_check = check_password_strength(user.password)
    if not password_check["is_valid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password does not meet security requirements. " + " ".join(password_check["errors"])
        )
    
    # Check if user already exists
    existing_user = UserDB.get_by_email(user.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create user
    password_hash = hash_password(user.password)
    user_id = UserDB.create(
        email=user.email,
        password_hash=password_hash,
        full_name=user.full_name,
        role=user.role.value
    )
    
    return UserDB.get_by_id(user_id)


@router.post("/login", response_model=Token)
async def login(credentials: UserLogin):
    """Login user and get JWT token"""
    # Get user
    user = UserDB.get_by_email(credentials.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Verify password
    if not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Create token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user["id"]), "role": user["role"]},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "email": user["email"],
            "full_name": user["full_name"],
            "role": user["role"],
            "created_at": user["created_at"]
        }
    }


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user = None):
    """Get current user info"""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    user = UserDB.get_by_id(current_user["user_id"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user
