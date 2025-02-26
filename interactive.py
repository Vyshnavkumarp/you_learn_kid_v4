import random
import json
from langchain_groq import ChatGroq
from langchain.prompts import PromptTemplate
import os
import ast

class InteractiveFeatures:
    def __init__(self):
        # Store conversation context
        self.conversation_topics = []
        # Initialize Groq LLM
        self.llm = ChatGroq(
            groq_api_key=os.getenv('GROQ_API_KEY'),
            model_name="mixtral-8x7b-32768"
        )
        
    def update_conversation_context(self, message):
        """Update the conversation context with new topics"""
        try:
            # Use Groq to extract topics from the conversation
            prompt = f"""
            Extract the main educational topics from this message:
            "{message}"
            
            Return only the topics as a comma-separated list. If no educational topics are found, return "general conversation".
            """
            
            response = self.llm.invoke(prompt)
            topics = response.content.strip().split(',')
            
            # Add topics to conversation context (max 5 recent topics)
            for topic in topics:
                topic = topic.strip()
                if topic and topic != "general conversation":
                    if topic not in self.conversation_topics:
                        self.conversation_topics.append(topic)
            
            # Keep only the 5 most recent topics
            self.conversation_topics = self.conversation_topics[-5:]
            
        except Exception as e:
            print(f"Error updating conversation context: {str(e)}")

    def should_generate_quiz(self, message):
        """Determine if we should generate a quiz based on the message"""
        # Convert message to lowercase for case-insensitive matching
        message_lower = message.lower()
        
        # Check for direct quiz requests
        quiz_keywords = ['quiz', 'test', 'question', 'questions', 'practice', 'exercise', 'test me']
        direct_requests = any(keyword in message_lower for keyword in quiz_keywords)
        
        # Check for phrases like "Can I have a quiz" or "I want a quiz"
        quiz_phrases = [
            'can i have a quiz', 
            'give me a quiz', 
            'i want a quiz',
            'create a quiz',
            'make a quiz',
            'test my knowledge'
        ]
        phrase_requests = any(phrase in message_lower for phrase in quiz_phrases)
        
        return direct_requests or phrase_requests

    def generate_quiz(self):
        """Generate a quiz based on conversation context or a random educational topic"""
        try:
            # Determine quiz topic
            if self.conversation_topics:
                topic = random.choice(self.conversation_topics)
            else:
                # Default topics if no conversation context
                default_topics = [
                    "Animals", "Space", "Math", "Science", "Geography", 
                    "History", "Technology", "Nature", "Art", "Music"
                ]
                topic = random.choice(default_topics)
            
            # Prompt for quiz generation
            prompt = f"""
            Create a kid-friendly quiz about {topic}. 
            Format:
            {{
                "topic": "{topic}",
                "questions": [
                    {{
                        "question": "Question text here?",
                        "options": ["Option A", "Option B", "Option C", "Option D"],
                        "correct_index": 0,
                        "explanation": "Brief explanation why this is correct"
                    }},
                    ... (2 more questions)
                ]
            }}
            
            Make sure:
            1. Questions are simple and age-appropriate for 6-14 year olds
            2. Use clear, straightforward language
            3. Provide exactly 3 questions
            4. Each question has 4 options
            5. correct_index is the 0-based index of the correct answer
            6. Include a short explanation for the correct answer
            7. Make it fun and engaging
            8. Return only valid JSON
            """
            
            response = self.llm.invoke(prompt)
            
            # Extract JSON from response
            import json
            import re
            
            # Look for JSON pattern
            json_match = re.search(r'({.*})', response.content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                quiz_data = json.loads(json_str)
                return quiz_data
            else:
                raise ValueError("Could not extract valid JSON from the quiz response")
            
        except Exception as e:
            print(f"Error generating quiz: {str(e)}")
            return None

    def get_learning_tip(self):
        """Get a random learning tip"""
        tips = [
            "Try explaining the concept to someone else to better understand it! 🎓",
            "Take short breaks between study sessions to stay focused! ⏰",
            "Write down key points to help remember them better! 📝",
            "Practice regularly to reinforce what you've learned! 🔄",
            "Connect new information to things you already know! 🧠",
            "Use mnemonics to remember complex information! 🎯",
            "Study in a quiet, well-lit environment! 💡",
            "Get enough sleep to help your brain process information! 😴",
            "Stay hydrated and maintain a healthy diet for better focus! 🥤",
            "Set specific learning goals for each study session! 🎯"
        ]
        return random.choice(tips)
