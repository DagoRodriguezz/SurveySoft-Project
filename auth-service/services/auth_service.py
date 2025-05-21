from werkzeug.security import generate_password_hash, check_password_hash
from models.user import User
from database import SessionLocal
from sqlalchemy.exc import IntegrityError


def create_user(username, password, role='user'):
    session = SessionLocal()

    # Verifica si el nombre de usuario ya existe
    existing_user = session.query(User).filter_by(username=username).first()
    if existing_user:
        session.close()
        return None

    try:
        hashed_password = generate_password_hash(password)
        user = User(username=username, password=hashed_password, role=role)
        session.add(user)
        session.commit()
        return user
    except IntegrityError:
        session.rollback()
        return None
    finally:
        session.close()

def authenticate_user(username, password):
    session = SessionLocal()
    user = session.query(User).filter_by(username=username).first()
    session.close()

    # Verifica si el usuario existe y la contraseña es correcta
    if user and check_password_hash(user.password, password):
        return user
    return None
