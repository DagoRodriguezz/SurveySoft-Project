from flask import Flask
from controllers.auth_controller import auth_bp
from database import init_db

app = Flask(__name__)

# Clave secreta para la sesión
app.secret_key = 'auth_service_secret_key_12345'

# Registra el blueprint de autenticación
app.register_blueprint(auth_bp, url_prefix='/auth')


# Inicializa la base de datos
with app.app_context():
    init_db()

if __name__ == '__main__':
    app.run(port=5001, debug=True)
