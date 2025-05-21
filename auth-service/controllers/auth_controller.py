from flask import Blueprint, request, render_template, redirect, url_for, session, flash
from services.auth_service import create_user, authenticate_user

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = authenticate_user(username, password)  # Obtén el usuario autenticado
        if user:
            session['user_id'] = user.id  # Guarda el ID del usuario en la sesión
            session['username'] = user.username
            session['role'] = user.role
            flash("Inicio de sesión exitoso.")
            
            # Redirige según el rol
            if user.role == 'admin':
                return redirect(url_for('auth.admin_dashboard'))
            elif user.role == 'user':
                return redirect(url_for('auth.user_dashboard'))
        else:
            flash("Usuario o contraseña incorrectos.")
    return render_template('auth/login.html')

# Ruta para el dashboard de admin
@auth_bp.route('/admin/dashboard')
def admin_dashboard():
    if 'role' not in session or session['role'] != 'admin':
        flash("No tienes permiso para acceder a esta página.")
        return redirect(url_for('auth.login'))
    return render_template('auth/admin_dashboard.html', username=session['username'])

@auth_bp.route('/user/dashboard')
def user_dashboard():
    if 'role' not in session or session['role'] != 'user':
        flash("No tienes permiso para acceder a esta página.")
        return redirect(url_for('auth.login'))
    return render_template(
        'auth/dashboard.html',
        username=session['username'],
        user_id=session['user_id']  # Pasa el user_id a la plantilla
    )


# Ruta para el registro
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = create_user(username, password)
        if user is None:
            flash("El usuario ya existe.")
        else:
            flash("Registro exitoso.")
            return redirect(url_for('auth.login'))
    return render_template('auth/register.html')

# Ruta para cerrar sesión
@auth_bp.route('/logout')
def logout():
    session.clear()
    flash("Sesión cerrada exitosamente.")
    return redirect(url_for('auth.login'))
