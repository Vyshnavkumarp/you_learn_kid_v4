from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User
from datetime import datetime
from email_validator import validate_email, EmailNotValidError

auth = Blueprint('auth', __name__)
login_manager = LoginManager()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('chat'))
    
    if request.method == 'GET':
        return render_template('login.html')
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.verify_password(password):
            login_user(user)
            user.last_login = datetime.utcnow()
            db.session.commit()
            return redirect(url_for('chat'))
        else:
            flash('Invalid username or password', 'error')
            return render_template('login.html')

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('chat'))
    
    if request.method == 'GET':
        return render_template('register.html')
    
    if request.method == 'POST':
        try:
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password')
            first_name = request.form.get('first_name')
            last_name = request.form.get('last_name', '')
            age = request.form.get('age')
            parent_email = request.form.get('parent_email', None)
            
            # Validate required fields
            required_fields = ['username', 'email', 'password', 'first_name', 'age']
            for field in required_fields:
                if not request.form.get(field):
                    flash(f'{field.replace("_", " ").title()} is required', 'error')
                    return render_template('register.html')
            
            # Validate email format
            try:
                valid = validate_email(email)
                email = valid.email
            except EmailNotValidError as e:
                flash(f'Invalid email: {str(e)}', 'error')
                return render_template('register.html')
            
            # If parent_email is provided, validate it
            if parent_email:
                try:
                    valid_parent = validate_email(parent_email)
                    parent_email = valid_parent.email
                except EmailNotValidError:
                    parent_email = None  # Reset if invalid
            
            # Check if username or email already exists
            if User.query.filter_by(username=username).first():
                flash('Username already exists', 'error')
                return render_template('register.html')
                
            if User.query.filter_by(email=email).first():
                flash('Email already registered', 'error')
                return render_template('register.html')
            
            # Create new user
            new_user = User(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                age=int(age),
                parent_email=parent_email
            )
            
            db.session.add(new_user)
            db.session.commit()
            
            # Log the user in
            login_user(new_user)
            
            return redirect(url_for('chat'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred during registration: {str(e)}', 'error')
            return render_template('register.html')

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

@auth.route('/profile')
@login_required
def get_profile():
    try:
        return jsonify({
            'user': current_user.to_dict()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth.route('/profile', methods=['PUT'])
@login_required
def update_profile():
    try:
        data = request.get_json()
        user = current_user
        
        # Update allowed fields
        allowed_fields = ['first_name', 'last_name', 'age']
        for field in allowed_fields:
            if field in data:
                setattr(user, field, data[field])
        
        db.session.commit()
        
        return jsonify({
            'message': 'Profile updated successfully',
            'user': user.to_dict()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
