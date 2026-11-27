# Access code endpoints used by the frontend gate screen

from fastapi import APIRouter, Depends

from app.security import access_code_required, require_access_code

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/status")
async def auth_status():
    """Tells the frontend whether an access code is needed (public)."""
    return {"required": access_code_required()}


@router.post("/verify", dependencies=[Depends(require_access_code)])
async def verify_access_code():
    """Returns 200 if the X-Access-Code header is valid, 401 otherwise."""
    return {"ok": True}
