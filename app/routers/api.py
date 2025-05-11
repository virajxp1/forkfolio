from fastapi import APIRouter
from app.core.config import settings

router = APIRouter(prefix=settings.API_V1_STR)

@router.get("/")
def root():
    return {"message": "Welcome to ForkFolio API"}

# Import and include other routers here
# from app.routers import items, users
# router.include_router(users.router, prefix="/users", tags=["Users"])
# router.include_router(items.router, prefix="/items", tags=["Items"])