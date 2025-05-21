import os

# Configuración de la URI de la base de datos MySQL
DATABASE_URI = os.getenv("DATABASE_URI", "mysql+pymysql://root:40621407Dago.@localhost:3306/question_service_db")

# Configuración del servicio
DATABASE_URL = "mysql+pymysql://root:40621407Dago.@localhost:3306/question_service_db"
SECRET_KEY = "auth_service_secret_key_12345"  # Usa una clave única y segura

