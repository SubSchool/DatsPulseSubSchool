from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.test_api import router as test_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(test_router, prefix="/test") 