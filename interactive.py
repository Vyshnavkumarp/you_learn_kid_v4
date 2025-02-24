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
            topic_prompt = PromptTemplate(
                template="""Extract 1-3 specific educational topics from this message. 
                Response must be EXACTLY in this format: ["topic1", "topic2"]
                
                Message: {message}
                """,
                input_variables=["message"]
            )
            
            response = self.llm.invoke(topic_prompt.format(message=message))
            topics = ast.literal_eval(response.content)
            
            # Update conversation topics
            self.conversation_topics.extend(topics)
            # Keep only the last 5 topics
            self.conversation_topics = self.conversation_topics[-5:]
            
        except Exception as e:
            print(f"Error updating conversation context: {str(e)}")

    def should_generate_quiz(self, message):
        """Determine if we should generate a quiz based on the message"""
        quiz_keywords = ['quiz', 'test', 'question', 'practice', 'exercise']
        return any(keyword in message.lower() for keyword in quiz_keywords)

    def generate_quiz(self):
        """Generate a quiz based on conversation context or a random educational topic"""
        try:
            topics = self.conversation_topics if self.conversation_topics else ["general knowledge"]
            topic = random.choice(topics)
            
            quiz_prompt = PromptTemplate(
                template="""Create a multiple-choice quiz question about {topic}.
                Response must be EXACTLY in this format:
                {{
                    "question": "What is...",
                    "options": ["option1", "option2", "option3", "option4"],
                    "correct_index": 0
                }}
                Make sure the correct_index matches the index of the correct answer in the options list.
                """,
                input_variables=["topic"]
            )
            
            response = self.llm.invoke(quiz_prompt.format(topic=topic))
            quiz_data = json.loads(response.content)
            return quiz_data
            
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
