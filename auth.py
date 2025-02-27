from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User
from datetime import datetime
from email_validator import validate_email, EmailNotValidError
from werkzeug.security import generate_password_hash, check_password_hash

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
        
        # Add debug logging
        print(f"Login attempt for user: {username}")
        
        # Find user by username (case-insensitive)
        user = User.query.filter(User.username.ilike(username)).first()
        
        if user:
            # Debug the password verification
            print(f"User found: {user.username}")
            
            # Use the verify_password method instead of check_password_hash
            password_matches = user.verify_password(password)
            print(f"Password match: {password_matches}")
            
            if password_matches:
                login_user(user, remember=True)
                
                # Update login streak
                today = datetime.now().date()
                if not user.last_login or (today - user.last_login.date()).days == 1:
                    # Consecutive day login
                    user.login_streak += 1
                elif (today - user.last_login.date()).days > 1:
                    # Streak broken
                    user.login_streak = 1
                
                user.last_login = datetime.now()
                db.session.commit()
                
                # Redirect based on referring page
                next_page = request.args.get('next')
                return redirect(next_page or url_for('chat'))
            else:
                flash('Invalid username or password.', 'error')
        else:
            flash('Invalid username or password.', 'error')
            
        return redirect(url_for('auth.login'))
    
    return render_template('login.html')

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('chat'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        age = request.form.get('age')
        parent_email = request.form.get('parent_email')
        
        # Check if username or email already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists.', 'error')
            return redirect(url_for('auth.register'))
        
        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            flash('Email already registered.', 'error')
            return redirect(url_for('auth.register'))
        
        # Create user with direct password hash setting to bypass any issues with the setter
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        
        # Create new user - use _password directly to bypass property setter
        new_user = User(
            username=username,
            email=email,
            _password=hashed_password,  # Use the private attribute directly
            first_name=first_name,
            last_name=last_name,
            age=age,
            parent_email=parent_email,
            created_at=datetime.now(),
            last_login=datetime.now(),
            login_streak=1,
            level=1,
            total_xp=0
        )
        
        try:
            db.session.add(new_user)
            db.session.commit()
            flash('Account created successfully! Please login.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating account: {str(e)}', 'error')
            print(f"Registration error: {str(e)}")
            return redirect(url_for('auth.register'))
    
    return render_template('register.html')

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
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
