from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from database import SessionLocal
from models.risk_matrix import RiskMatrix 
from models.survey import  EvaluationForm
from sqlalchemy.exc import SQLAlchemyError
from flask import current_app

risk_bp = Blueprint('risk', __name__)

@risk_bp.route('/', methods=['GET', 'POST'])
def manage_risks():
    session_db = SessionLocal()
    try:
        if request.method == 'POST':
            # Recibir datos del formulario
            software_id = request.form['software_id']
            description = request.form['description']
            probability = request.form['probability']
            impact = request.form['impact']
            risk_level = request.form['risk_level']
            mitigation = request.form.get('mitigation', '')

            # Crear un nuevo riesgo
            new_risk = RiskMatrix(
                software_id=software_id,
                description=description,
                probability=probability,
                impact=impact,
                risk_level=risk_level,
                mitigation=mitigation
            )
            session_db.add(new_risk)
            session_db.commit()
            flash("Riesgo agregado exitosamente.", "success")
            return redirect(url_for('risk.manage_risks'))

        # Obtener todos los riesgos y los formularios de software
        risks = session_db.query(RiskMatrix, EvaluationForm.software_name).join(
            EvaluationForm, RiskMatrix.software_id == EvaluationForm.id
        ).all()
        software_list = session_db.query(EvaluationForm).all()
        return render_template('risk/manage_risk.html', risks=risks, software_list=software_list)
    except SQLAlchemyError as e:
        session_db.rollback()
        flash("Ocurrió un error al gestionar los riesgos.", "error")
        print(str(e))
        return redirect(url_for('risk.manage_risks'))
    finally:
        session_db.close()