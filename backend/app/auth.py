"""Authenticatie configuratie en JWT handling."""
import os
import yaml
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging

logger = logging.getLogger(__name__)

SECRET_KEY = os.getenv("SECRET_KEY", "portfolio-dashboard-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24 uur

security = HTTPBearer()


def load_credentials():
    """Laad gebruikerscredentials uit configuratiebestand of omgevingsvariabelen."""
    config_path = os.getenv("AUTH_CONFIG_PATH", "/app/config/auth.yaml")
    
    # Probeer YAML config
    if os.path.exists(config_path):
        with open(config_path) as f:
            config = yaml.safe_load(f)
            return config.get("username", "admin"), config.get("password", "geheim123")
    
    # Fallback naar env vars
    return (
        os.getenv("AUTH_USERNAME", "admin"),
        os.getenv("AUTH_PASSWORD", "geheim123"),
    )


def verify_credentials(username: str, password: str) -> bool:
    """Verifieer gebruikersnaam en wachtwoord."""
    valid_username, valid_password = load_credentials()
    return username == valid_username and password == valid_password


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Maak een JWT access token aan."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Valideer JWT token en geef huidige gebruiker terug."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Ongeldige authenticatiegegevens",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        return username
    except JWTError:
        raise credentials_exception
