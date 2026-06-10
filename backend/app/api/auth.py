"""Authenticatie API endpoints."""
from fastapi import APIRouter, HTTPException, status
from app.schemas import LoginRequest, TokenResponse
from app.auth import verify_credentials, create_access_token

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest):
    """Inloggen met gebruikersnaam en wachtwoord."""
    if not verify_credentials(request.username, request.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Onjuiste gebruikersnaam of wachtwoord",
        )
    token = create_access_token(data={"sub": request.username})
    return TokenResponse(access_token=token)
