from sqlalchemy import Column, Integer, String, Enum, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class RiskMatrix(Base):
    __tablename__ = "risk_matrix"

    risk_id = Column(Integer, primary_key=True, autoincrement=True)
    software_id = Column(Integer, ForeignKey('evaluation_forms.id'), nullable=False)
    description = Column(String(255), nullable=False)
    probability = Column(Enum('Baja', 'Media', 'Alta'), nullable=False)
    impact = Column(Enum('Bajo', 'Medio', 'Alto'), nullable=False)
    risk_level = Column(Enum('Bajo', 'Moderado', 'Crítico'), nullable=False)
    mitigation = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relaciones
    software = relationship("EvaluationForm")
