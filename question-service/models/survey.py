from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, Float, func
from sqlalchemy.orm import relationship
import uuid
from database import Base


class Survey(Base):
    __tablename__ = 'survey'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relación con secciones y resultados
    sections = relationship('SurveySection', back_populates='survey', lazy="select")
    results = relationship('SurveyResults', back_populates='survey', lazy="select")


class SurveySection(Base):
    __tablename__ = "survey_section"
    id = Column(Integer, primary_key=True, autoincrement=True)
    survey_id = Column(Integer, ForeignKey("survey.id", ondelete="CASCADE"))
    section_title = Column(String(255))
    description = Column(Text)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    survey = relationship('Survey', back_populates='sections')
    items = relationship('SurveyItem', back_populates='section', lazy="select")


class SurveyItem(Base):
    __tablename__ = 'survey_item'

    id = Column(Integer, primary_key=True)
    section_id = Column(Integer, ForeignKey('survey_section.id', ondelete="CASCADE"))
    code = Column(String(50), nullable=True)  # Código único para cada pregunta
    item_name = Column(String(255))
    description = Column(Text)
    value = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relaciones
    section = relationship('SurveySection', back_populates='items')
    results = relationship('SurveyResults', back_populates='item')


class SurveyResults(Base):
    __tablename__ = "survey_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    survey_id = Column(Integer, ForeignKey("survey.id"), nullable=False)
    item_id = Column(Integer, ForeignKey("survey_item.id"), nullable=True)
    total_score = Column(Integer, nullable=False)
    percentage = Column(Float(3, 1), nullable=False)
    overall_result = Column(String(255), nullable=False)
    response_id = Column(String(36), nullable=False, unique=True, default=lambda: str(uuid.uuid4()))  # UUID
    form_id = Column(Integer, ForeignKey("evaluation_forms.id"), nullable=False)  # Relación con el formulario

    # Relaciones con otras tablas
    item = relationship("SurveyItem", back_populates="results")
    survey = relationship("Survey", back_populates="results")
    form = relationship("EvaluationForm", back_populates="results")  # Relación con el formulario


class SurveyResponse(Base):
    __tablename__ = 'survey_response'

    id = Column(Integer, primary_key=True, autoincrement=True)
    survey_id = Column(Integer, ForeignKey('survey.id', ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, nullable=False)
    item_id = Column(Integer, ForeignKey('survey_item.id', ondelete="CASCADE"), nullable=False)
    value = Column(Float(3, 1), nullable=True)  # Permitir nulo para respuestas en blanco

    # Relaciones
    survey = relationship("Survey")
    item = relationship("SurveyItem")


class EvaluationForm(Base):
    __tablename__ = "evaluation_forms"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(String(255), nullable=False)
    city = Column(String(255), nullable=False)
    company = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=False)
    software_name = Column(String(255), nullable=False)
    general_objectives = Column(String(500), nullable=False)
    specific_objectives = Column(String(500), nullable=False)
    created_at = Column(DateTime, default=func.now())

    # Relación con SurveyResults
    results = relationship("SurveyResults", back_populates="form")
