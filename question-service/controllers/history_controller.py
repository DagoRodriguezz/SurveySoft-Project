from flask import Blueprint, jsonify, render_template, flash, redirect, url_for, send_file, session
from services.survey_service import get_user_survey_history, get_survey_details
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO

history_bp = Blueprint('history', __name__)

@history_bp.route('/users/<int:user_id>/history', methods=['GET'])
def view_history(user_id):
    """
    Muestra el historial de encuestas realizadas por un usuario.
    """
    try:
        # Obtener historial del usuario
        history = get_user_survey_history(user_id)
        username = session.get('username', 'Usuario')  # Usar nombre de usuario si está en la sesión

        if not history:
            flash("No se encontraron encuestas realizadas por el usuario.")
            history = []  # Si no hay historial, devolver lista vacía

        return render_template('survey/history.html', history=history, username=username)
    except Exception as e:
        flash(f"Error al cargar el historial: {e}")
        return render_template('survey/history.html', history=[], username="Usuario", error=str(e))


@history_bp.route('/users/<int:user_id>/history/json', methods=['GET'])
def get_user_survey_history_endpoint(user_id):
    """
    Endpoint JSON para obtener el historial de encuestas de un usuario.
    """
    try:
        history = get_user_survey_history(user_id)
        if not history:
            return jsonify({"error": "No se encontró historial para este usuario."}), 404
        return jsonify({"user_id": user_id, "history": history}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@history_bp.route('/users/<int:user_id>/details/<int:survey_id>', methods=['GET'])
def survey_details(user_id, survey_id):
    """
    Muestra los detalles de una encuesta específica realizada por el usuario.
    """
    try:
        details = get_survey_details(survey_id)
        username = session.get('username', 'Usuario')  # Usar nombre de usuario si está en la sesión

        if not details:
            flash("No se encontraron detalles para esta encuesta.")
            return redirect(url_for('history.view_history', user_id=user_id))

        return render_template('survey/details.html', details=details, username=username)
    except Exception as e:
        flash(f"Error al cargar los detalles: {e}")
        return redirect(url_for('history.view_history', user_id=user_id))


@history_bp.route('/users/<int:user_id>/history/<int:survey_id>/download', methods=['GET'])
def download_survey_results_pdf(user_id, survey_id):
    """
    Genera un archivo PDF con los resultados de una encuesta y permite descargarlo.
    """
    try:
        # Obtener detalles de la encuesta para generar el PDF
        survey_details = get_survey_details(survey_id)
        if not survey_details:
            flash("No se encontraron detalles para generar el PDF.")
            return redirect(url_for('history.view_history', user_id=user_id))

        # Crear un archivo PDF en memoria
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        c.setFont("Helvetica", 12)

        # Título del PDF
        c.drawString(100, 750, f"Resultados de la Encuesta ID: {survey_id}")
        c.drawString(100, 730, f"Nombre de la Encuesta: {survey_details['survey_name']}")
        c.drawString(100, 710, f"Descripción: {survey_details['survey_description']}")

        # Detalles de las preguntas
        y = 690
        for section in survey_details["sections"]:
            if y < 100:  # Salto de página si se acaba el espacio
                c.showPage()
                y = 750

            c.drawString(100, y, f"Sección: {section['section_title']}")
            y -= 20

            for question in section["questions"]:
                if y < 100:
                    c.showPage()
                    y = 750
                c.drawString(120, y, f"- Pregunta: {question['item_name']}")
                c.drawString(140, y - 20, f"  {question['description']}")
                y -= 40

        c.save()

        # Preparar el PDF para la descarga
        buffer.seek(0)
        return send_file(buffer, as_attachment=True, download_name=f"survey_{survey_id}_results.pdf", mimetype='application/pdf')

    except Exception as e:
        flash(f"Error al generar el PDF: {e}")
        return redirect(url_for('history.view_history', user_id=user_id))
