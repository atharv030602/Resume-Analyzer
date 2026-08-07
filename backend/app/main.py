from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.routers import analysis

# Auto-create tables on startup (mirrors spring.jpa.hibernate.ddl-auto=update)
try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"WARNING: could not create DB tables, DB features disabled: {e}")

app = FastAPI(title="ResumeFit AI", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://resume-analyzer-nk4wmappwmh2hdz3prkoh4d.streamlit.app",
        "http://localhost:8501",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analysis.router)
