from flask import Blueprint, session, redirect, url_for, flash

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/logout', methods=['GET'])
def logout():
    # Limpiar la sesión
    session.clear()
    flash("Has cerrado sesión correctamente.")
    return redirect(url_for('question.surveys'))


@auth_bp.route('/user/dashboard', methods=['GET'])
def user_dashboard():
    if 'user_id' not in session:
        flash("Debes iniciar sesión para acceder al dashboard.")
        return redirect(url_for('auth.login'))

    # Verifica roles, si es necesario
    if session.get('role') != 'user':  # Cambia 'user' según el rol que corresponda
        flash("No tienes permiso para acceder a esta página.")
        return redirect(url_for('auth.login'))

    user_name = session.get('user_name', 'Usuario')
    return render_template('auth/dashboard.html', user_name=user_name)

