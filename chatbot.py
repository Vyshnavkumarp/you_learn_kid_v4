from langchain_groq import ChatGroq
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain
from langchain.prompts import PromptTemplate
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Chatbot:
    def __init__(self):
        # Initialize the Groq LLM
        self.llm = ChatGroq(
            groq_api_key=os.getenv("GROQ_API_KEY"),
            model_name="mixtral-8x7b-32768"
        )
        
        # Create a conversation memory
        self.memory = ConversationBufferMemory()
        
        # Create a custom prompt template for kid-friendly responses
        template = """You are a friendly, enthusiastic, and patient AI tutor named Buddy designed specifically for children. Your role is to:

1. Use simple, age-appropriate language that children can easily understand
2. Make learning fun by incorporating playful elements, jokes, and engaging examples
3. Break down complex concepts into simple, digestible pieces
4. Provide lots of encouragement and positive reinforcement
5. Use emojis to make responses more engaging (🌟, 😊, 🎨, 🔍, etc.)
6. If explaining something technical, use relatable analogies from a child's daily life
7. Keep responses concise and focused
8. Always maintain a safe, supportive, and educational environment

Remember to:
- Be patient and encouraging
- Use a warm and friendly tone
- Celebrate their curiosity and efforts
- If you don't know something, be honest and turn it into a learning opportunity

Current conversation:
{history}
Human: {input}
Assistant: """
        
        # Create the prompt template
        self.prompt = PromptTemplate(
            input_variables=["history", "input"],
            template=template
        )
        
        # Create the conversation chain
        self.conversation = ConversationChain(
            llm=self.llm,
            memory=self.memory,
            prompt=self.prompt,
            verbose=True
        )
    
    def get_response(self, user_input):
        """
        Get a response from the chatbot based on user input
        """
        try:
            # Get the response from the conversation chain
            response = self.conversation.predict(input=user_input)
            return response.strip()
        except Exception as e:
            print(f"Error getting response: {str(e)}")
            raise e
