document.addEventListener('DOMContentLoaded', () => {
    const chatMessages = document.getElementById('chat-messages');
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-button');
    const voiceButton = document.getElementById('voice-input');
    const quizContainer = document.getElementById('quiz-container');
    const tipContainer = document.getElementById('tip-container');
    const loadingElement = document.getElementById('loading');
    const closeQuizButton = document.getElementById('close-quiz');

    let currentQuiz = null;
    let isProcessing = false;

    function addMessage(message, isUser = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${isUser ? 'user-message' : 'bot-message'}`;
        
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        messageContent.textContent = message;
        
        messageDiv.appendChild(messageContent);
        chatMessages.appendChild(messageDiv);
        
        // Scroll to bottom
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function showLoading() {
        loadingElement.classList.remove('hidden');
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function hideLoading() {
        loadingElement.classList.add('hidden');
    }

    function displayQuiz(quiz) {
        currentQuiz = quiz;
        const quizContent = quizContainer.querySelector('.quiz-content');
        const questionElement = quizContent.querySelector('.quiz-question');
        const optionsElement = quizContent.querySelector('.quiz-options');
        const feedbackElement = quizContent.querySelector('.quiz-feedback');
        
        questionElement.textContent = quiz.question;
        optionsElement.innerHTML = '';
        feedbackElement.innerHTML = '';
        
        quiz.options.forEach((option, index) => {
            const button = document.createElement('button');
            button.className = 'quiz-option';
            button.textContent = option;
            button.onclick = () => checkAnswer(index);
            optionsElement.appendChild(button);
        });
        
        quizContainer.classList.remove('hidden');
    }

    function displayTip(tip) {
        const tipContent = tipContainer.querySelector('.tip-content');
        tipContent.textContent = tip;
        tipContainer.classList.remove('hidden');
    }

    async function checkAnswer(selectedIndex) {
        if (!currentQuiz) return;
        
        const quizContent = quizContainer.querySelector('.quiz-content');
        const optionsElement = quizContent.querySelector('.quiz-options');
        const feedbackElement = quizContent.querySelector('.quiz-feedback');
        const buttons = optionsElement.querySelectorAll('button');
        
        // Disable all buttons
        buttons.forEach(button => button.disabled = true);
        
        try {
            const response = await fetch('/check_answer', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    selected_index: selectedIndex,
                    correct_index: currentQuiz.correct_index
                })
            });
            
            if (!response.ok) throw new Error('Failed to check answer');
            
            const data = await response.json();
            feedbackElement.innerHTML = `
                <div class="quiz-feedback-content ${data.is_correct ? 'correct' : 'incorrect'}">
                    <i class="fas ${data.is_correct ? 'fa-check-circle' : 'fa-times-circle'}"></i>
                    <p>${data.feedback}</p>
                </div>
            `;
            
            // Highlight correct and incorrect answers
            buttons.forEach((button, index) => {
                if (index === currentQuiz.correct_index) {
                    button.classList.add('correct');
                } else if (index === selectedIndex && !data.is_correct) {
                    button.classList.add('incorrect');
                }
            });
            
        } catch (error) {
            console.error('Error checking answer:', error);
            feedbackElement.textContent = 'Error checking answer. Please try again.';
        }
    }

    function closeQuiz() {
        quizContainer.classList.add('hidden');
        const feedbackElement = quizContainer.querySelector('.quiz-feedback');
        feedbackElement.innerHTML = '';
        currentQuiz = null;
    }

    async function sendMessage() {
        if (isProcessing || !userInput.value.trim()) return;
        
        const message = userInput.value.trim();
        userInput.value = '';
        addMessage(message, true);
        
        showLoading();
        isProcessing = true;
        
        try {
            const response = await fetch('/send_message', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ message })
            });
            
            if (!response.ok) throw new Error('Failed to send message');
            
            const data = await response.json();
            
            hideLoading();
            addMessage(data.response);
            
            if (data.quiz) {
                displayQuiz(data.quiz);
            }
            
            if (data.learning_tip) {
                displayTip(data.learning_tip);
            }
            
        } catch (error) {
            console.error('Error sending message:', error);
            hideLoading();
            addMessage('Sorry, I encountered an error. Please try again.');
        }
        
        isProcessing = false;
    }

    // Voice input handling
    if ('webkitSpeechRecognition' in window) {
        const recognition = new webkitSpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;
        
        recognition.onstart = () => {
            voiceButton.classList.add('listening');
        };
        
        recognition.onend = () => {
            voiceButton.classList.remove('listening');
        };
        
        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            userInput.value = transcript;
            sendMessage();
        };
        
        voiceButton.addEventListener('click', () => {
            recognition.start();
        });
    } else {
        voiceButton.style.display = 'none';
    }

    // Event listeners
    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    sendButton.addEventListener('click', sendMessage);
    closeQuizButton.addEventListener('click', closeQuiz);

    // Generate quiz button
    document.getElementById('generate-quiz').addEventListener('click', async () => {
        showLoading();
        try {
            const response = await fetch('/generate_quiz');
            if (!response.ok) throw new Error('Failed to generate quiz');
            
            const quiz = await response.json();
            hideLoading();
            displayQuiz(quiz);
        } catch (error) {
            console.error('Error generating quiz:', error);
            hideLoading();
            addMessage('Sorry, I encountered an error generating the quiz. Please try again.');
        }
    });
});
