from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta, timezone

from app.database import get_db
from app.models import User, RefreshToken
from app.schemas import UserCreate, UserResponse, UserLogin, Token, RefreshTokenRequest
from app.auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_refresh_token,
    revoke_refresh_token,
    get_current_user
)
from app.utils.exceptions import UserAlreadyExistsError, InvalidCredentialsError
from app.config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    """
    Register a new user.

    - **email**: Valid email address
    - **password**: Minimum 8 characters
    - **first_name**: User's first name
    - **last_name**: User's last name
    """
    # Check if user already exists
    result = await db.execute(select(User).where(User.email == user_data.email))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise UserAlreadyExistsError(user_data.email)

    # Create new user
    try:
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"About to hash password of length: {len(user_data.password)}")
        hashed = get_password_hash(user_data.password)
        logger.info(f"Password hashed successfully: {hashed[:20]}")

        user = User(
            email=user_data.email,
            password_hash=hashed,
            first_name=user_data.first_name,
            last_name=user_data.last_name
        )

        db.add(user)
        await db.commit()
        await db.refresh(user)

        return user
    except Exception as e:
        import traceback
        logger.error(f"Registration error: {str(e)}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    Login with email and password to get access and refresh tokens.

    OAuth2 compatible endpoint. Use:
    - **username**: User's email
    - **password**: User's password
    """
    # Find user by email
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.password_hash):
        raise InvalidCredentialsError()

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account"
        )

    # Update last login
    user.last_login = datetime.now(timezone.utc)


    # Create tokens
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token_str = create_refresh_token(data={"sub": str(user.id)})

    # Store refresh token in database
    refresh_token = RefreshToken(
    user_id=user.id,
    token=refresh_token_str,
    expires_at=datetime.now(timezone.utc)+ timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
)

    db.add(refresh_token)

    await db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token_str,
        "token_type": "bearer"
    }


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh access token using a valid refresh token.

    - **refresh_token**: Valid refresh token obtained from login
    """
    user = await verify_refresh_token(refresh_data.refresh_token, db)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )

    # Revoke old refresh token
    await revoke_refresh_token(refresh_data.refresh_token, db)

    # Create new tokens
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token_str = create_refresh_token(data={"sub": str(user.id)})

    # Store new refresh token
    refresh_token = RefreshToken(
        user_id=user.id,
        token=refresh_token_str,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    db.add(refresh_token)

    await db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token_str,
        "token_type": "bearer"
    }


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    refresh_data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Logout by revoking the refresh token.

    - **refresh_token**: Refresh token to revoke
    """
    await revoke_refresh_token(refresh_data.refresh_token, db)
    return None


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user information.
    """
    return current_user
