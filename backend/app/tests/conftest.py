import os

# A configuração é lida na importação de app.main; garante um valor padrão fora do container.
os.environ.setdefault("DATABASE_URL", "postgresql://lastro_app:x@localhost:5432/lastro")
