import uuid
from models.survey import Survey, SurveyItem, SurveySection, SurveyResults, SurveyResponse, EvaluationForm
from database import SessionLocal
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import IntegrityError
from flask import current_app
from sqlalchemy.sql import func

def get_all_surveys():
    session = SessionLocal()
    try:
        predefined_surveys = session.query(Survey).filter(
            Survey.name.in_(['ISO 25000 Evaluation', 'IEEE 730 Evaluation', 'FURPS Evaluation', 'Boehm Model Evaluation'])
        ).all()
        return predefined_surveys
    finally:
        session.close()


def get_survey_by_id(survey_id):
    session = SessionLocal()
    try:
        return session.query(Survey).options(
            joinedload(Survey.sections).joinedload(SurveySection.items)
        ).filter(Survey.id == survey_id).one_or_none()
    finally:
        session.close()


def save_evaluation_form(data):
    """
    Guarda un formulario de evaluación y retorna su ID.
    """
    session = SessionLocal()
    try:
        form = EvaluationForm(
            date=data['date'],
            city=data['city'],
            company=data['company'],
            phone=data['phone'],
            software_name=data['software_name'],
            general_objectives=data['general_objectives'],
            specific_objectives=data['specific_objectives']
        )
        session.add(form)
        session.commit()
        return form.id
    except Exception as e:
        session.rollback()
        current_app.logger.error(f"Error al guardar el formulario: {e}")
        raise e
    finally:
        session.close()


def clone_survey(original_survey_id, form_id, user_id):
    session = SessionLocal()
    try:
        original_survey = session.query(Survey).filter(Survey.id == original_survey_id).one_or_none()
        if not original_survey:
            raise ValueError("Encuesta original no encontrada.")

        cloned_survey = Survey(
            name=f"{original_survey.name} - {uuid.uuid4()}",
            description=original_survey.description,
        )
        session.add(cloned_survey)
        session.commit()

        for section in original_survey.sections:
            cloned_section = SurveySection(
                survey_id=cloned_survey.id,
                section_title=section.section_title,
                description=section.description,
            )
            session.add(cloned_section)
            session.commit()

            for item in section.items:
                cloned_item = SurveyItem(
                    section_id=cloned_section.id,
                    code=f"ITEM-{uuid.uuid4()}",
                    item_name=item.item_name,
                    description=item.description,
                    value=0,
                )
                session.add(cloned_item)

        session.commit()

        questions = session.query(SurveyItem).filter(SurveyItem.section_id.in_(
            [section.id for section in cloned_survey.sections]
        )).all()

        for question in questions:
            response = SurveyResponse(
                survey_id=cloned_survey.id,
                user_id=user_id,
                item_id=question.id,
                value=0
            )
            session.add(response)

        session.commit()
        return cloned_survey.id
    except Exception as e:
        session.rollback()
        current_app.logger.error(f"Error al clonar encuesta: {e}")
        raise e
    finally:
        session.close()


def get_results_by_survey(survey_id, user_id):
    """
    Obtiene los resultados de la encuesta, incluyendo secciones, preguntas y la norma asociada.
    """
    session = SessionLocal()
    try:
        current_app.logger.debug(f"Buscando resultados de la encuesta {survey_id} para el usuario {user_id}")
        
        # Consultar la encuesta para obtener su norma (nombre)
        survey = session.query(Survey).filter(Survey.id == survey_id).one_or_none()
        if not survey:
            raise ValueError(f"No se encontró la encuesta con ID {survey_id}")

        # Consultar respuestas de la encuesta
        responses = session.query(SurveyResponse).options(
            joinedload(SurveyResponse.item).joinedload(SurveyItem.section)
        ).filter(
            SurveyResponse.survey_id == survey_id,
            SurveyResponse.user_id == user_id
        ).all()

        if not responses:
            raise ValueError(f"No se encontraron respuestas para la encuesta con ID {survey_id} del usuario {user_id}")

        # Estructurar los resultados y convertir Decimal a float
        results = [
            {
                "section_title": response.item.section.section_title,
                "item_name": response.item.item_name,
                "description": response.item.description,
                "value": float(response.value) if response.value is not None else 0.0,
                "max_value": 3.0,  # Supongamos que el valor máximo por respuesta es 3
                "percentage": (float(response.value) / 3.0) * 100 if response.value is not None else 0.0
            }
            for response in responses
        ]

        # Calcular totales
        total_score = sum(result["value"] for result in results)
        max_score = len(results) * 3
        overall_percentage = (total_score / max_score) * 100 if max_score > 0 else 0.0
        overall_result = calculate_overall_result(overall_percentage)

        current_app.logger.debug(f"Resultados procesados: {results}")

        return {
            "results": results,
            "total_score": float(total_score),
            "max_score": float(max_score),
            "overall_percentage": round(overall_percentage, 2),
            "overall_result": overall_result,
            "norm": survey.name  # Agregar la norma asociada
        }
    except Exception as e:
        current_app.logger.error(f"Error al obtener resultados de la encuesta {survey_id}: {e}")
        raise e
    finally:
        session.close()





def calculate_overall_result(percentage):
    """
    Calcula el resultado general basado en el porcentaje.
    """
    if percentage > 90:
        return "Excelente"
    elif percentage > 70:
        return "Sobresaliente"
    elif percentage > 50:
        return "Aceptable"
    elif percentage > 30:
        return "Insuficiente"
    else:
        return "Deficiente"


def get_form_data(form_id):
    """
    Obtiene los datos de un formulario basado en su ID.
    """
    session = SessionLocal()
    try:
        form = session.query(EvaluationForm).filter(EvaluationForm.id == form_id).one_or_none()
        if not form:
            raise ValueError(f"No se encontró el formulario con ID {form_id}")
        
        return {
            "date": form.date,
            "city": form.city,
            "company": form.company,
            "phone": form.phone,
            "software_name": form.software_name,
            "general_objectives": form.general_objectives,
            "specific_objectives": form.specific_objectives,
        }
    except Exception as e:
        current_app.logger.error(f"Error al obtener los datos del formulario: {e}")
        raise e
    finally:
        session.close()



def get_filtered_responses(survey_id, user_id):
    """
    Obtiene solo las respuestas más recientes por pregunta (item_id) para un usuario en una encuesta específica.
    """
    session = SessionLocal()
    try:
        latest_responses = session.query(
            SurveyResponse.item_id,
            func.max(SurveyResponse.id).label("latest_id")
        ).filter(
            SurveyResponse.survey_id == survey_id,
            SurveyResponse.user_id == user_id
        ).group_by(SurveyResponse.item_id).subquery()

        responses = session.query(SurveyResponse).join(
            latest_responses, SurveyResponse.id == latest_responses.c.latest_id
        ).options(
            joinedload(SurveyResponse.item).joinedload(SurveyItem.section)
        ).all()

        return responses
    except Exception as e:
        current_app.logger.error(f"Error al filtrar respuestas: {e}")
        raise e
    finally:
        session.close()


def get_user_survey_history(user_id):
    """
    Obtiene el historial de encuestas realizadas por un usuario.
    """
    session = SessionLocal()
    try:
        results = (
            session.query(SurveyResults)
            .join(Survey, SurveyResults.survey_id == Survey.id)
            .filter(SurveyResults.user_id == user_id)
            .all()
        )
        history = [
            {
                "survey_id": result.survey_id,
                "survey_name": result.survey.name,
                "total_score": result.total_score,
                "percentage": result.percentage,
                "overall_result": result.overall_result,
                "completed_at": result.created_at,
            }
            for result in results
        ]
        return history
    except Exception as e:
        current_app.logger.error(f"Error al obtener el historial de encuestas del usuario {user_id}: {e}")
        raise e
    finally:
        session.close()


        
def get_survey_details(survey_id):
    """
    Obtiene los detalles de una encuesta específica (secciones y preguntas).
    """
    session = SessionLocal()
    try:
        survey = session.query(Survey).filter(Survey.id == survey_id).one_or_none()
        if not survey:
            raise ValueError(f"No se encontró la encuesta con ID {survey_id}.")

        # Obtener secciones y preguntas relacionadas
        sections = session.query(SurveySection).filter(SurveySection.survey_id == survey_id).all()
        questions = session.query(SurveyItem).join(SurveySection).filter(SurveySection.survey_id == survey_id).all()

        # Estructurar los detalles de la encuesta
        survey_details = {
            "survey_name": survey.name,
            "survey_description": survey.description,
            "sections": [
                {
                    "section_title": section.section_title,
                    "description": section.description,
                    "questions": [
                        {
                            "item_name": question.item_name,
                            "description": question.description,
                            "code": question.code,
                            "value": question.value
                        }
                        for question in questions if question.section_id == section.id
                    ]
                }
                for section in sections
            ]
        }

        return survey_details
    except Exception as e:
        current_app.logger.error(f"Error al obtener detalles de la encuesta {survey_id}: {e}")
        raise e
    finally:
        session.close()
