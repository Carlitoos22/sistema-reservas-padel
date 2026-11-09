import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# ===== CONEXION A LA BASE DE DATOS =====
# En local usa Postgres en localhost:15432; en la nube usa la variable DATABASE_URL.
URL_BASE_DATOS = os.getenv(
    "DATABASE_URL",
    "postgresql+pg8000://padel_user:padel_pass@localhost:15432/padel_db",
)

# SSL para la base en la nube (Neon/Render lo piden). En local queda apagado.
connect_args = {}
if os.getenv("DB_SSL", "false").lower() == "true":
    import ssl
    connect_args["ssl_context"] = ssl.create_default_context()

engine = create_engine(URL_BASE_DATOS, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()