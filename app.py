from flask import Flask, request, jsonify, render_template, send_file
from flask_cors import CORS
from chatbot import Chatbot
from interactive import InteractiveFeatures
import os
import random

app = Flask(__name__)
CORS(app)

# Initialize the chatbot and interactive features
chatbot = Chatbot()
interactive = InteractiveFeatures()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/send_message', methods=['POST'])
def send_message():
    user_message = request.json.get('message', '')
    
    try:
        # Get response from the chatbot
        response = chatbot.get_response(user_message)
        
        # Generate speech file
        speech_file = interactive.text_to_speech(response)
        
        # Update conversation context
        interactive.update_conversation_context(user_message)
        
        # Get learning tip
        tip = interactive.get_learning_tip(None)
        
        # Generate quiz if message contains quiz-related keywords
        if any(word in user_message.lower() for word in ['quiz', 'test', 'question']):
            quiz = interactive.generate_quiz_with_llm(user_message)
            return jsonify({
                'response': response,
                'quiz': quiz,
                'speech_available': True,
                'tip': tip
            })
        
        return jsonify({
            'response': response,
            'speech_available': True,
            'tip': tip
        })
        
    except Exception as e:
        print(f"Error in send_message: {str(e)}")
        return jsonify({
            'response': "I'm having trouble understanding. Could you try asking that again?",
            'speech_available': False
        })

@app.route('/check_answer', methods=['POST'])
def check_answer():
    try:
        data = request.json
        user_answer = data.get('answer', '')
        question = data.get('question', {})
        
        if not question or not user_answer:
            return jsonify({'error': 'Invalid request data'}), 400
            
        result = interactive.check_answer(question, user_answer)
        return jsonify(result)
    except Exception as e:
        print(f"Error checking answer: {str(e)}")
        return jsonify({'error': 'Error checking answer'}), 500

@app.route('/get_speech', methods=['GET'])
def get_speech():
    try:
        speech_file = os.path.join('temp', 'speech.mp3')
        if os.path.exists(speech_file):
            return send_file(speech_file, mimetype='audio/mp3')
        return jsonify({'error': 'Speech file not found'}), 404
    except Exception as e:
        print(f"Error getting speech: {str(e)}")
        return jsonify({'error': 'Error getting speech file'}), 500

@app.route('/generate_quiz', methods=['GET'])
def generate_quiz():
    try:
        # Generate quiz using current conversation context
        quiz = interactive.generate_quiz_with_llm()
        return jsonify({
            'quiz': quiz,
            'tip': interactive.get_learning_tip(None)
        })
    except Exception as e:
        print(f"Error generating quiz: {str(e)}")
        return jsonify({'error': 'Error generating quiz'}), 500

if __name__ == '__main__':
    os.makedirs('temp', exist_ok=True)
    app.run(debug=True)
