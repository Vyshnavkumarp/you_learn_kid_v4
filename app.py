from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
from flask_cors import CORS
import os
from dotenv import load_dotenv
from chatbot import Chatbot
from interactive import InteractiveFeatures
from models import db, LearningSession, QuizAttempt, User, Achievement, UserAchievement
from auth import auth, login_manager
from progress import progress, initialize_achievements, check_quiz_achievements
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
        return redirect(url_for('progress.dashboard'))
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
        
        # Check if we should generate a quiz
        quiz_mode = interactive.should_generate_quiz(message)
        
        # Get response from chatbot
        response = chatbot.get_response(message)
        
        # Update conversation context
        interactive.update_conversation_context(message)
        
        # Return response with possible quiz
        result = {'response': response}
        
        # 30% chance to add a learning tip
        if random.random() < 0.3:
            result['tip'] = interactive.get_learning_tip()
            
        # Generate quiz if in quiz mode
        if quiz_mode:
            quiz = interactive.generate_quiz()
            if quiz:
                result['quiz'] = quiz
        
        # Record learning session
        session = LearningSession(
            user_id=current_user.id,
            topic="General Chat",
            duration_minutes=1,
            xp_earned=1
        )
        db.session.add(session)
        db.session.commit()
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/check_answer', methods=['POST'])
@login_required
def check_answer():
    try:
        data = request.json
        
        # Validate required fields
        required_fields = ['quiz_id', 'question_index', 'selected_answer']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Get session quiz data (this would be stored in your session or cache)
        # For this example, we'll simulate checking answers
        
        is_correct = data['selected_answer'] == data.get('correct_answer', 0)
        
        # If it's the last question, record quiz attempt
        if data.get('is_last_question', False):
            quiz_attempt = QuizAttempt(
                user_id=current_user.id,
                topic=data.get('topic', 'General Knowledge'),
                score=data.get('current_score', 0) + (1 if is_correct else 0),
                max_score=data.get('total_questions', 1)
            )
            db.session.add(quiz_attempt)
            
            # Add XP for completing quiz
            xp_earned = quiz_attempt.score * 2  # 2 XP per correct answer
            current_user.add_xp(xp_earned)
            
            db.session.commit()
            
            # Check for achievements
            check_quiz_achievements(quiz_attempt)
            
            return jsonify({
                'is_correct': is_correct,
                'message': 'Quiz completed!',
                'xp_earned': xp_earned,
                'quiz_complete': True
            })
        
        return jsonify({
            'is_correct': is_correct,
            'message': 'Correct! Great job!' if is_correct else 'Not quite. Try again!'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/generate_quiz')
@login_required
def generate_quiz():
    try:
        # Generate quiz using the conversation context
        quiz = interactive.generate_quiz()
        
        if quiz:
            # Record a learning session for the quiz generation
            session = LearningSession(
                user_id=current_user.id,
                topic=quiz.get('topic', 'Quiz'),
                duration_minutes=1,
                xp_earned=1
            )
            db.session.add(session)
            db.session.commit()
            
            return jsonify(quiz)
        else:
            return jsonify({'error': 'Failed to generate quiz'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
