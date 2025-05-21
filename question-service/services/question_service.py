# services/question_service.py

from models.survey import Survey
from database import SessionLocal

def get_questions():
    """Obtiene todas las preguntas."""
    session = SessionLocal()
    questions = session.query(Survey).all()
    session.close()
    return questions

def create_question(question_data):
    """Crea una nueva pregunta."""
    session = SessionLocal()
    question = Survey(**question_data)
    session.add(question)
    session.commit()
    session.close()
    return question

def update_question(question_id, question_data):
    """Actualiza una pregunta existente."""
    session = SessionLocal()
    question = session.query(Survey).filter_by(id=question_id).first()
    if question:
        for key, value in question_data.items():
            setattr(question, key, value)
        session.commit()
    session.close()
    return question

def delete_question(question_id):
    """Elimina una pregunta."""
    session = SessionLocal()
    question = session.query(Survey).filter_by(id=question_id).first()
    if question:
        session.delete(question)
        session.commit()
    session.close()
