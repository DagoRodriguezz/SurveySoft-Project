import os

# Configuración de la URI de la base de datos MySQL
# DATABASE_URI = "mysql+pymysql://root:Manchas12345.@localhost:3308/auth_service_db"

import os

SECRET_KEY = "auth_service_secret_key_12345"  # Usa una clave única y segura

# Configuración de la base de datos
DATABASE_URL = os.getenv('DATABASE_URL', 'mysql+pymysql://root:40621407Dago.@localhost:3306/auth_service_db')
