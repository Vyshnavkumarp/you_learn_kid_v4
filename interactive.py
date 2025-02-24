import pyttsx3
import speech_recognition as sr
import random
import json
from gtts import gTTS
import os
import tempfile
from langchain_groq import ChatGroq
from langchain.prompts import PromptTemplate
import ast

class InteractiveFeatures:
    def __init__(self):
        # Initialize text-to-speech engine
        self.engine = pyttsx3.init()
        # Initialize speech recognizer
        self.recognizer = sr.Recognizer()
        # Store conversation context
        self.conversation_topics = []
        # Initialize Groq LLM
        self.llm = ChatGroq(
            groq_api_key=os.getenv('GROQ_API_KEY'),
            model_name="mixtral-8x7b-32768"
        )
        
    def text_to_speech(self, text):
        """Convert text to speech and return audio file path"""
        try:
            # Create a temporary file
            temp_dir = tempfile.gettempdir()
            temp_file = os.path.join(temp_dir, 'speech.mp3')
            
            # Generate speech
            tts = gTTS(text=text, lang='en')
            tts.save(temp_file)
            
            return temp_file
        except Exception as e:
            print(f"Error in text_to_speech: {str(e)}")
            return None

    def update_conversation_context(self, message):
        """Update the conversation context with new topics"""
        print(f"\nUpdating conversation context with message: {message}")  # Debug log
        try:
            # Use Groq to extract topics from the conversation
            topic_prompt = PromptTemplate(
                template="""Extract 1-3 specific educational topics from this message. 
                Response must be EXACTLY in this format: ["topic1", "topic2"]
                
                Message: {message}
                
                Rules:
                1. Be very specific (e.g., "volcanoes" not "science", "addition" not "math")
                2. Only include topics actually mentioned in the message
                3. Maximum 3 topics
                4. Format must be valid Python list of strings
                5. Topics must be lowercase
                
                Examples:
                Message: "I love learning about volcanoes and earthquakes!"
                ["volcanoes", "earthquakes"]
                
                Message: "Can you teach me about addition?"
                ["addition"]
                
                Message: "I want to learn about planets and rockets"
                ["planets", "rockets"]
                """,
                input_variables=["message"]
            )
            
            print("Extracting topics using LLM...")  # Debug log
            # Get topics from LLM
            topic_response = self.llm.invoke(topic_prompt.format(message=message))
            print(f"LLM Response: {topic_response.content}")  # Debug log
            
            # Parse the response into a list
            try:
                new_topics = ast.literal_eval(topic_response.content)
                if isinstance(new_topics, list):
                    # Add new topics to conversation context
                    for topic in new_topics:
                        if topic not in self.conversation_topics:
                            self.conversation_topics.append(topic)
                    # Keep only the 5 most recent topics
                    self.conversation_topics = self.conversation_topics[-5:]
                    print(f"Updated conversation topics: {self.conversation_topics}")  # Debug log
            except Exception as parse_error:
                print(f"Error parsing topics: {str(parse_error)}")
                
        except Exception as e:
            print(f"Error updating conversation context: {str(e)}")
            # Fallback to keyword matching if LLM fails
            message = message.lower()
            topic_keywords = {
                'addition': ['addition', 'plus', 'sum', 'add'],
                'subtraction': ['subtraction', 'minus', 'subtract', 'difference'],
                'multiplication': ['multiplication', 'times', 'multiply', 'product'],
                'division': ['division', 'divide', 'quotient'],
                'planets': ['planets', 'mars', 'jupiter', 'saturn', 'solar system'],
                'dinosaurs': ['dinosaurs', 't-rex', 'triceratops', 'prehistoric'],
                'volcanoes': ['volcanoes', 'lava', 'eruption', 'magma'],
                'weather': ['weather', 'rain', 'snow', 'wind', 'storm'],
                'animals': ['animals', 'lions', 'tigers', 'elephants', 'pets'],
                'human body': ['body', 'heart', 'brain', 'muscles', 'bones'],
                'plants': ['plants', 'trees', 'flowers', 'seeds', 'leaves']
            }
            
            for topic, keywords in topic_keywords.items():
                if any(keyword in message for keyword in keywords):
                    if topic not in self.conversation_topics:
                        self.conversation_topics.append(topic)
                        if len(self.conversation_topics) > 5:
                            self.conversation_topics.pop(0)
            print(f"Fallback topics: {self.conversation_topics}")  # Debug log

    def generate_quiz_with_llm(self, context_message=None):
        """Generate a quiz using Groq LLM based on conversation context"""
        try:
            # Update context if message provided
            if context_message:
                self.update_conversation_context(context_message)
            
            print(f"\nGenerating quiz. Current topics: {self.conversation_topics}")  # Debug log
            
            # Get topics from conversation or use general knowledge
            if self.conversation_topics:
                # Use conversation topics for context-based quiz
                topic = random.choice(self.conversation_topics)
                print(f"Selected topic for quiz: {topic}")  # Debug log
                
                prompt = PromptTemplate(
                    template="""Generate a quiz question about {topic} for children.
                    Response MUST be in this EXACT format:
                    {{
                        "question": "Your question here?",
                        "options": ["option1", "option2", "option3", "option4"],
                        "correct": "correct option here"
                    }}
                    
                    Rules:
                    1. Question must be SPECIFICALLY about {topic}
                    2. Use child-friendly language
                    3. Include emojis
                    4. All options must be reasonable
                    5. Correct answer must match one option exactly
                    
                    Examples for different topics:
                    
                    Topic: volcanoes
                    {{
                        "question": "What hot liquid comes out of a volcano? 🌋",
                        "options": ["Lava", "Water", "Juice", "Milk"],
                        "correct": "Lava"
                    }}
                    
                    Topic: addition
                    {{
                        "question": "What is 5 + 3? 🔢",
                        "options": ["8", "6", "7", "9"],
                        "correct": "8"
                    }}
                    """,
                    input_variables=["topic"]
                )
            else:
                print("No conversation topics found, generating random quiz")  # Debug log
                # Generate random fun quiz
                topics = [
                    "fun facts about animals", "interesting science facts", 
                    "basic math puzzles", "world geography for kids",
                    "colors and shapes", "fun riddles", "nature facts",
                    "space and planets", "dinosaurs", "ocean life"
                ]
                topic = random.choice(topics)
                prompt = PromptTemplate(
                    template="""Generate a fun quiz question about {topic} for children.
                    Response MUST be in this EXACT format:
                    {{
                        "question": "Your question here?",
                        "options": ["option1", "option2", "option3", "option4"],
                        "correct": "correct option here"
                    }}
                    
                    Rules:
                    1. Make it fun and surprising
                    2. Use simple language
                    3. Include emojis
                    4. Make it educational
                    5. All options should be plausible
                    6. Correct answer must match one option exactly
                    """,
                    input_variables=["topic"]
                )
            
            # Generate quiz using Groq
            print(f"Generating quiz for topic: {topic}")  # Debug log
            quiz_response = self.llm.invoke(prompt.format(topic=topic))
            print(f"Quiz response: {quiz_response.content}")  # Debug log
            
            # Parse the response into a dictionary
            quiz_dict = ast.literal_eval(quiz_response.content)
            
            # Validate quiz format
            if not all(key in quiz_dict for key in ["question", "options", "correct"]):
                raise ValueError("Invalid quiz format")
            if len(quiz_dict["options"]) != 4:
                raise ValueError("Quiz must have exactly 4 options")
            if quiz_dict["correct"] not in quiz_dict["options"]:
                raise ValueError("Correct answer must be one of the options")
            
            return quiz_dict
            
        except Exception as e:
            print(f"Error generating quiz with Groq: {str(e)}")
            try:
                # Try a simpler prompt
                simple_prompt = PromptTemplate(
                    template="""Create a very simple children's quiz question.
                    Format:
                    {{
                        "question": "Which animal says meow? 🐱",
                        "options": ["Cat", "Dog", "Bird", "Fish"],
                        "correct": "Cat"
                    }}
                    """,
                    input_variables=[]
                )
                fallback_response = self.llm.invoke(simple_prompt.format())
                return ast.literal_eval(fallback_response.content)
            except Exception as e2:
                print(f"Error in fallback quiz generation: {str(e2)}")
                # Return a different hardcoded quiz each time
                fallback_quizzes = [
                    {
                        "question": "What makes a rainbow appear in the sky? 🌈",
                        "options": ["Sunlight and Rain", "Magic Dust", "Wind", "Clouds"],
                        "correct": "Sunlight and Rain"
                    },
                    {
                        "question": "Which animal is known as the king of the jungle? 🦁",
                        "options": ["Lion", "Tiger", "Elephant", "Giraffe"],
                        "correct": "Lion"
                    },
                    {
                        "question": "What do astronauts travel in to go to space? 🚀",
                        "options": ["Spaceship", "Car", "Boat", "Bicycle"],
                        "correct": "Spaceship"
                    }
                ]
                return random.choice(fallback_quizzes)

    def check_answer(self, question, user_answer):
        """Check if the answer is correct and return feedback"""
        if user_answer.lower() == question['correct'].lower():
            return {
                "correct": True,
                "message": "🎉 Great job! That's correct! You're so smart! 🌟",
                "points": 10
            }
        else:
            return {
                "correct": False,
                "message": f"Nice try! 💫 The correct answer is {question['correct']}. Let's learn from this! 📚",
                "points": 0
            }

    def get_learning_tip(self, topic):
        """Get a random learning tip based on the conversation context"""
        tips = {
            "math": [
                "Try drawing pictures to help solve math problems! 🎨",
                "Break big numbers into smaller parts to make them easier to work with! 🔢",
                "Practice counting with objects you find at home! 🏠"
            ],
            "science": [
                "Try simple experiments at home with adult supervision! 🔬",
                "Look for science in everyday life - like watching plants grow! 🌱",
                "Ask lots of questions about how things work! ❓"
            ],
            "history": [
                "Make a timeline of events to understand when things happened! 📅",
                "Draw pictures of historical events to remember them better! 🎨",
                "Share historical stories with your friends and family! 📚"
            ],
            "geography": [
                "Look at maps when you hear about different places! 🗺️",
                "Learn about different cultures and their traditions! 🌍",
                "Try to find places you know on a globe! 🌎"
            ],
            "language": [
                "Read your favorite stories out loud! 📖",
                "Practice writing new words you learn! ✏️",
                "Play word games with your friends! 🎮"
            ]
        }
        
        # Choose tip based on conversation context or default to general
        available_topics = list(set(self.conversation_topics) & set(tips.keys()))
        if available_topics:
            topic = random.choice(available_topics)
            return random.choice(tips[topic])
        return "Keep being curious and asking questions! 🌟"
