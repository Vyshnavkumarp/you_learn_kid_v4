from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
from flask_cors import CORS
import os
from dotenv import load_dotenv
from chatbot import Chatbot
from interactive import InteractiveFeatures
from models import db
from auth import auth, login_manager
from progress import progress, initialize_achievements
from flask_login import login_required, current_user
import random

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Configure SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///youlearn.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-here')

# Initialize extensions
db.init_app(app)
login_manager.init_app(app)

# Configure login manager
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'error'

# Register blueprints
app.register_blueprint(auth, url_prefix='/auth')
app.register_blueprint(progress, url_prefix='/progress')

# Create database tables
with app.app_context():
    db.create_all()
    initialize_achievements()  # Initialize default achievements

# Initialize the chatbot and interactive features
chatbot = Chatbot()
interactive = InteractiveFeatures()

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('chat'))
    return redirect(url_for('auth.login'))

@app.route('/chat')
@login_required
def chat():
    return render_template('index.html')

@app.route('/send_message', methods=['POST'])
@login_required
def send_message():
    try:
        data = request.json
        message = data.get('message', '')
        
        if not message:
            return jsonify({'error': 'No message provided'}), 400
        
        # Get response from chatbot
        response = chatbot.get_response(message)
        
        # Check if we should generate a quiz
        should_generate_quiz = interactive.should_generate_quiz(message)
        quiz_data = interactive.generate_quiz() if should_generate_quiz else None
        
        # Get a learning tip
        learning_tip = interactive.get_learning_tip() if random.random() < 0.3 else None
        
        return jsonify({
            'response': response,
            'quiz': quiz_data,
            'learning_tip': learning_tip
        })
        
    except Exception as e:
        print(f"Error in send_message: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/check_answer', methods=['POST'])
@login_required
def check_answer():
    try:
        data = request.json
        selected_index = data.get('selected_index')
        correct_index = data.get('correct_index')
        
        is_correct = selected_index == correct_index
        feedback = "Correct! Well done! " if is_correct else "Not quite right. Keep trying! "
        
        return jsonify({
            'is_correct': is_correct,
            'feedback': feedback
        })
        
    except Exception as e:
        print(f"Error in check_answer: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/generate_quiz')
@login_required
def generate_quiz():
    try:
        quiz_data = interactive.generate_quiz()
        return jsonify(quiz_data)
    except Exception as e:
        print(f"Error in generate_quiz: {str(e)}")
        return jsonify({'error': 'Failed to generate quiz'}), 500

if __name__ == '__main__':
    app.run(debug=True)
