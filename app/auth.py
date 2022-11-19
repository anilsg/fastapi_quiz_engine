"""
Manage password hashing, authentication, and oAuth2 compliant JOSE/JWT access tokens.
To remain oAuth2 compliant "username" field must be used for the log in.
JWT tokens pack expiry datetime and email ("username") as the subject ("sub") field.
Future use could include packing scopes for authorisation.
JWT settings such as the signature for signing the tokens are taken from the environment.
"""
from datetime import datetime, timedelta
import bcrypt  # https://pypi.org/project/bcrypt/
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from models import JWTSettings, User, TokenData
from db import get_user, save_user


jwt_settings = JWTSettings()
JWT_SIGNATURE = jwt_settings.jwt_signature
JWT_ALGORITHM = jwt_settings.jwt_algorithm
JWT_EXPIRE_MINUTES = jwt_settings.jwt_expire_minutes

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def password_hash(plain_password: str) -> str:
    """Generate and return salted Blowfish password hash."""
    hashed_password = bcrypt.hashpw(plain_password.encode('utf-8'), bcrypt.gensalt())
    return hashed_password.decode('utf-8')  # Do not return bytes


def password_check(plain_password: str, hashed_password: str):
    """Given plain password return True if it matches provided salted hash from password_hash."""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


def authenticate_user(username: str, password: str):
    """Return UserRec object for provided username (email) iff provided plain password matches."""
    user = get_user(username)
    if user and password_check(password, user.hashed):
        return user
    return False


def create_access_token(data: dict):
    """
    Return JOSE/JWT oAuth2 compliant signed access token with packed expiry and provided data.
    Data expected to contain oAuth2 compliant subject field containing oAuth2 username (email).
    """
    expiry = datetime.utcnow() + timedelta(minutes=JWT_EXPIRE_MINUTES)
    data = data.copy()  # {"sub": "<username>"} username expected to be email
    data.update({"exp": expiry})
    encoded_jwt_access_token = jwt.encode(data, JWT_SIGNATURE, algorithm=JWT_ALGORITHM)
    return encoded_jwt_access_token


def create_new_user(user: dict):
    """Create new User."""
    if get_user(user["email"]):
        return None
    user["hashed"] = password_hash(user["plain"])
    user = save_user(user)
    return user


async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Return currently authenticated user (without active check) or raise 401 unauthorized."""
    try:
        payload = jwt.decode(token, JWT_SIGNATURE, algorithms=[JWT_ALGORITHM])
        username: str = payload.get("sub")
        if username:
            token_data = TokenData(username=username)
            user = get_user(username=token_data.username)
            if user:
                return user
    except JWTError:
        pass
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials", headers={"WWW-Authenticate": "Bearer"}
    )


async def get_current_active_user(current_user: User = Depends(get_current_user)):
    """Return currently authenticated user with check for active or raise 401 unauthorized."""
    if current_user.active:
        return current_user
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
