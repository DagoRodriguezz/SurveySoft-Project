from flask import Blueprint, request,render_template, redirect, url_for, session, flash, current_app, send_file
from services.survey_service import (
    get_all_surveys,
    get_survey_by_id,
    save_evaluation_form,
    clone_survey,
    get_results_by_survey,
    calculate_overall_result,
    get_form_data  
)
from database import SessionLocal
from models.survey import SurveyResults, SurveyResponse
from reportlab.lib.pagesizes import letter, landscape
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer , Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from io import BytesIO
from uuid import uuid4
from sqlalchemy.sql import func
from sqlalchemy.orm import joinedload
from models.survey import Survey, SurveyItem, SurveySection, SurveyResults, SurveyResponse, EvaluationForm
import time  



question_bp = Blueprint('question', __name__)

# Ruta para listar encuestas
@question_bp.route('/surveys', methods=['GET'])
def surveys():
    if 'role' not in session or session['role'] != 'admin':
        flash("No tienes permiso para acceder a esta página.")
        return redirect('http://localhost:5001/auth/login')

    surveys = get_all_surveys()
    return render_template('survey/home.html', surveys=surveys)

# Ruta para el formulario inicial
@question_bp.route('/formulario', methods=['GET', 'POST'])
def formulario():
    if request.method == 'POST':
        data = {
            'date': request.form['date'],
            'city': request.form['city'],
            'company': request.form['company'],
            'phone': request.form['phone'],
            'software_name': request.form['software_name'],
            'general_objectives': request.form['general_objectives'],
            'specific_objectives': request.form['specific_objectives']
        }

        try:
            current_app.logger.debug(f"Datos del formulario recibidos: {data}")
            form_id = save_evaluation_form(data)  # Guarda solo el formulario
            session['form_id'] = form_id  # Guarda el ID del formulario en la sesión
            flash("Formulario guardado exitosamente.")
            return redirect(url_for('question.select_survey'))  # Redirige a seleccionar encuesta
        except Exception as e:
            current_app.logger.error(f"Error al guardar el formulario: {e}")
            flash(f"Error al guardar el formulario: {e}", "error")

    return render_template('question/formulario.html')

# Ruta para seleccionar encuesta
@question_bp.route('/surveys/select', methods=['GET', 'POST'])
def select_survey():
    current_app.logger.debug("Accediendo a la ruta para seleccionar encuesta.")
    if 'user_id' not in session:
        flash("Debes iniciar sesión para seleccionar una encuesta.")
        return redirect('http://localhost:5001/auth/login')

    surveys = get_all_surveys()  # Obtén las encuestas disponibles

    if request.method == 'POST':
        selected_survey_id = request.form.get('survey_id')  # Obtén el ID de la encuesta seleccionada
        form_id = session.get('form_id')  # ID del formulario actual
        user_id = session.get('user_id')  # ID del usuario actual

        if selected_survey_id:
            try:
                current_app.logger.debug(f"Encuesta seleccionada: {selected_survey_id}")
                cloned_survey_id = clone_survey(selected_survey_id, form_id, user_id)
                session['survey_id'] = cloned_survey_id  # Guarda la encuesta en la sesión
                flash("Encuesta seleccionada exitosamente.")
                return redirect(url_for('question.complete_survey_view', survey_id=cloned_survey_id))
            except Exception as e:
                current_app.logger.error(f"Error al procesar la encuesta seleccionada: {e}")
                flash(f"Error al procesar la encuesta seleccionada: {e}", "error")
        else:
            flash("Por favor selecciona una encuesta.", "error")

    return render_template('survey/select_survey.html', surveys=surveys)

# Ruta para completar la encuesta
@question_bp.route('/surveys/<int:survey_id>/complete', methods=['GET', 'POST'])
def complete_survey_view(survey_id):
    session_db = SessionLocal()
    try:
        if request.method == 'GET':
            survey = get_survey_by_id(survey_id)
            if not survey:
                flash("Encuesta no encontrada.", "error")
                return redirect(url_for('question.select_survey'))
            return render_template('survey/complete_survey.html', survey=survey)

        elif request.method == 'POST':
            user_id = session.get('user_id')
            form_id = session.get('form_id')

            if not user_id or not form_id:
                flash("Faltan datos del usuario o formulario.", "error")
                return redirect(url_for('question.select_survey'))

            total_score = 0
            max_score = 0

            for key, value in request.form.items():
                if key.startswith('item_'):
                    try:
                        item_id = int(key.split('_')[1])
                        score = int(value)
                        total_score += score
                        max_score += 3  # Supongamos que el puntaje máximo por ítem es 3
                        response = SurveyResponse(
                            survey_id=survey_id,
                            user_id=user_id,
                            item_id=item_id,
                            value=score
                        )
                        session_db.add(response)
                    except ValueError:
                        current_app.logger.error(f"Valor inválido para el ítem {key}.")
                    except Exception as e:
                        current_app.logger.error(f"Error procesando respuesta para {key}: {e}")

            session_db.commit()

            percentage = (total_score / max_score) * 100 if max_score > 0 else 0
            overall_result = calculate_overall_result(percentage)

            survey_result = SurveyResults(
                user_id=user_id,
                survey_id=survey_id,
                total_score=total_score,
                percentage=percentage,
                overall_result=overall_result,
                form_id=form_id,
                response_id=str(uuid4())
            )
            session_db.add(survey_result)
            session_db.commit()

            flash("Encuesta completada exitosamente.", "success")
            return redirect(url_for('question.download_survey_results_pdf', survey_id=survey_id))

    except Exception as e:
        session_db.rollback()
        current_app.logger.error(f"Error al procesar la encuesta con ID {survey_id}: {e}")
        flash("Hubo un error al procesar la encuesta.", "error")
        return redirect(url_for('question.select_survey'))
    finally:
        session_db.close()

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
)
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO

@question_bp.route('/surveys/<int:survey_id>/results/pdf', methods=['GET'])
def download_survey_results_pdf(survey_id):
    """
    Genera un PDF estilizado con los resultados de la encuesta, ajustando datos largos automáticamente.
    """
    session_db = SessionLocal()
    try:
        user_id = session.get('user_id')  # Obtener el usuario desde la sesión de Flask
        if not user_id:
            flash("No se pudo identificar al usuario.", "error")
            return redirect(url_for('question.surveys'))

        # Obtener las respuestas filtradas
        latest_responses = session_db.query(
            SurveyResponse.item_id,
            func.max(SurveyResponse.id).label("latest_id")
        ).filter(
            SurveyResponse.survey_id == survey_id,
            SurveyResponse.user_id == user_id
        ).group_by(SurveyResponse.item_id).subquery()

        responses = session_db.query(SurveyResponse).join(
            latest_responses, SurveyResponse.id == latest_responses.c.latest_id
        ).options(
            joinedload(SurveyResponse.item).joinedload(SurveyItem.section)
        ).all()

        if not responses:
            flash("No se encontraron respuestas para esta encuesta.", "error")
            return redirect(url_for('question.surveys'))

        # Obtener datos adicionales de la encuesta y formulario
        survey = session_db.query(Survey).filter(Survey.id == survey_id).one_or_none()
        form_data = get_form_data(session.get('form_id'))

        # Calcular puntajes totales y porcentaje general
        total_score = sum(response.value for response in responses if response.value is not None)
        max_score = len(responses) * 3  # Suponiendo que el valor máximo por pregunta es 3
        overall_percentage = (total_score / max_score) * 100 if max_score > 0 else 0.0
        overall_result = calculate_overall_result(overall_percentage)

        # Crear un archivo PDF en memoria
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(letter))

        # Estilos
        styles = getSampleStyleSheet()
        title_style = styles['Title']
        title_style.textColor = colors.HexColor('#2C3E50')
        title_style.fontSize = 20

        normal_style = styles['Normal']
        normal_style.fontSize = 10

        table_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495E')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#ECF0F1'), colors.white]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#BDC3C7')),
        ])

        # Elementos del PDF
        elements = []

        # Título y encabezado del reporte
        elements.append(Paragraph("Reporte de Evaluación", title_style))
        elements.append(Spacer(1, 20))
        elements.append(Paragraph(f"<b>Encuesta ID:</b> {survey_id}", normal_style))
        elements.append(Paragraph(f"<b>Software evaluado:</b> {form_data['software_name']}", normal_style))
        elements.append(Paragraph(f"<b>Empresa:</b> {form_data['company']}", normal_style))
        elements.append(Paragraph(f"<b>Norma de evaluación:</b> {survey.name}", normal_style))
        elements.append(Paragraph(f"<b>Resultado General:</b> {overall_result}", normal_style))
        elements.append(Paragraph(f"<b>Porcentaje Total:</b> {round(overall_percentage, 2)}%", normal_style))
        elements.append(Paragraph(f"<b>Puntaje Total:</b> {round(total_score, 0)}/{max_score}", normal_style))
        elements.append(Spacer(1, 24))

        # Tabla de resultados
        data = [["Sección", "Pregunta", "Descripción", "Valor", "Porcentaje"]]
        for response in responses:
            section_title = response.item.section.section_title
            item_name = response.item.item_name
            description = Paragraph(response.item.description, normal_style)  # Envolver texto
            value = response.value
            max_value = 3  # Valor máximo por respuesta
            percentage = (value / max_value) * 100 if value is not None else 0.0
            data.append([
                section_title,
                item_name,
                description,
                f"{round(value, 0)}/{max_value}",
                f"{round(percentage, 2)}%"
            ])

        table = Table(data, colWidths=[100, 100, 200, 50, 70])  # Ajustar ancho de columnas
        table.setStyle(table_style)
        elements.append(table)

        # Dividir tabla si es necesario
        elements.append(PageBreak())  # Dividir páginas automáticamente si los datos son extensos

        # Generar PDF
        doc.build(elements)

        # Crear respuesta para el cliente
        buffer.seek(0)
        return send_file(buffer, as_attachment=True, download_name=f"survey_{survey_id}_results.pdf", mimetype='application/pdf')

    except Exception as e:
        current_app.logger.error(f"Error al generar el PDF de resultados: {e}")
        flash("Hubo un error al generar el archivo PDF.", "error")
        return redirect(url_for('question.surveys'))
    finally:
        session_db.close()

@question_bp.route('/surveys/<int:survey_id>/administer', methods=['GET'])
def administer_survey(survey_id):
    """
    Vista para administrar una encuesta (listar preguntas, crear, actualizar, eliminar).
    """
    session_db = SessionLocal()
    try:
        current_app.logger.info(f"Iniciando administración de la encuesta con ID: {survey_id}")
        
        # Obtener la encuesta con sus secciones y preguntas
        survey = session_db.query(Survey).filter(Survey.id == survey_id).one_or_none()
        if not survey:
            flash("Encuesta no encontrada.", "error")
            current_app.logger.error(f"Encuesta con ID {survey_id} no encontrada.")
            return redirect(url_for('question.surveys'))
        
        # Obtener preguntas asociadas a la encuesta
        questions = (
            session_db.query(SurveyItem, SurveySection)
            .join(SurveySection, SurveyItem.section_id == SurveySection.id)
            .filter(SurveySection.survey_id == survey_id)
            .all()
        )

        current_app.logger.info(f"Encuesta encontrada: {survey.name}")
        current_app.logger.debug(f"Preguntas encontradas: {len(questions)} preguntas para la encuesta {survey_id}")

        return render_template(
            'survey/administer_survey.html',
            survey=survey,
            questions=[
                {
                    'id': q[0].id,
                    'item_name': q[0].item_name,
                    'description': q[0].description,
                    'section_title': q[1].section_title  # Cambio realizado aquí
                }
                for q in questions
            ]
        )
    except Exception as e:
        current_app.logger.error(f"Error al administrar la encuesta con ID {survey_id}: {e}")
        flash("Hubo un error al cargar la encuesta.", "error")
        return redirect(url_for('question.surveys'))
    finally:
        session_db.close()



@question_bp.route('/surveys/<int:survey_id>/questions/new', methods=['GET', 'POST'])
def create_question(survey_id):
    """
    Crear una nueva pregunta para una encuesta con un código generado automáticamente.
    """
    session_db = SessionLocal()
    try:
        current_app.logger.info(f"Iniciando creación de una nueva pregunta para la encuesta con ID: {survey_id}")
        
        if request.method == 'POST':
            item_name = request.form['item_name']
            description = request.form['description']
            section_id = request.form['section_id']

            current_app.logger.debug(f"Datos recibidos del formulario: item_name={item_name}, description={description}, section_id={section_id}")
            
            # Generar automáticamente un código único para la pregunta
            timestamp = int(time.time())
            code = f"Q{survey_id}_{timestamp}"  # Ejemplo: Q4_1690672953
            current_app.logger.info(f"Código generado automáticamente para la pregunta: {code}")

            # Crear y guardar la pregunta
            question = SurveyItem(
                item_name=item_name,
                description=description,
                section_id=section_id,
                code=code,
                value=0  # Valor inicial por defecto
            )
            session_db.add(question)
            session_db.commit()

            current_app.logger.info(f"Pregunta creada exitosamente con ID: {question.id} y código: {code}")
            flash("Pregunta creada exitosamente.", "success")
            return redirect(url_for('question.administer_survey', survey_id=survey_id))

        # Obtener secciones de la encuesta para asignar la pregunta a una sección
        sections = session_db.query(SurveySection).filter(SurveySection.survey_id == survey_id).all()
        current_app.logger.debug(f"Secciones obtenidas para la encuesta con ID {survey_id}: {sections}")
        return render_template('survey/new_question.html', sections=sections, survey_id=survey_id)
    except Exception as e:
        current_app.logger.error(f"Error al crear una pregunta para la encuesta con ID {survey_id}: {e}")
        flash("Hubo un error al crear la pregunta.", "error")
        return redirect(url_for('question.administer_survey', survey_id=survey_id))
    finally:
        current_app.logger.debug("Cerrando la sesión de la base de datos.")
        session_db.close()




@question_bp.route('/surveys/<int:survey_id>/questions/<int:question_id>/edit', methods=['GET', 'POST'])
def edit_question(survey_id, question_id):
    """
    Editar una pregunta existente de una encuesta.
    """
    session_db = SessionLocal()
    try:
        question = session_db.query(SurveyItem).filter(SurveyItem.id == question_id).one_or_none()
        if not question:
            flash("Pregunta no encontrada.", "error")
            current_app.logger.warning(f"Pregunta con ID {question_id} no encontrada en la encuesta {survey_id}")
            return redirect(url_for('question.administer_survey', survey_id=survey_id))

        if request.method == 'POST':
            question.item_name = request.form['item_name']
            question.description = request.form['description']
            session_db.commit()

            flash("Pregunta actualizada exitosamente.", "success")
            current_app.logger.info(f"Pregunta actualizada exitosamente: {question.item_name}")
            return redirect(url_for('question.administer_survey', survey_id=survey_id))

        return render_template('survey/edit_question.html', question=question, survey_id=survey_id)
    except Exception as e:
        current_app.logger.error(f"Error al editar la pregunta con ID {question_id} en la encuesta {survey_id}: {e}")
        flash("Hubo un error al actualizar la pregunta.", "error")
        return redirect(url_for('question.administer_survey', survey_id=survey_id))
    finally:
        session_db.close()


@question_bp.route('/surveys/<int:survey_id>/questions/<int:question_id>/delete', methods=['POST'])
def delete_question(survey_id, question_id):
    """
    Eliminar una pregunta de una encuesta.
    """
    session_db = SessionLocal()
    try:
        question = session_db.query(SurveyItem).filter(SurveyItem.id == question_id).one_or_none()
        if not question:
            flash("Pregunta no encontrada.", "error")
            current_app.logger.warning(f"Intento de eliminar pregunta no existente con ID {question_id} en encuesta {survey_id}")
            return redirect(url_for('question.administer_survey', survey_id=survey_id))

        session_db.delete(question)
        session_db.commit()

        flash("Pregunta eliminada exitosamente.", "success")
        current_app.logger.info(f"Pregunta eliminada exitosamente: {question_id}")
        return redirect(url_for('question.administer_survey', survey_id=survey_id))
    except Exception as e:
        current_app.logger.error(f"Error al eliminar la pregunta con ID {question_id} en la encuesta {survey_id}: {e}")
        flash("Hubo un error al eliminar la pregunta.", "error")
        return redirect(url_for('question.administer_survey', survey_id=survey_id))
    finally:
        session_db.close()
