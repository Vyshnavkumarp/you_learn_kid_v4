document.addEventListener('DOMContentLoaded', () => {
    const chatMessages = document.getElementById('chat-messages');
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-button');
    const voiceButton = document.getElementById('voice-input');
    const soundButton = document.getElementById('toggle-sound');
    const quizContainer = document.getElementById('quiz-container');
    const tipContainer = document.getElementById('tip-container');
    const loadingElement = document.getElementById('loading');
    const closeQuizButton = document.getElementById('close-quiz');

    let soundEnabled = true;
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

    async function playResponse(text) {
        if (!soundEnabled) return;
        
        try {
            const response = await fetch('/get_speech');
            if (!response.ok) throw new Error('Failed to get speech');
            
            const blob = await response.blob();
            const audio = new Audio(URL.createObjectURL(blob));
            await audio.play();
        } catch (error) {
            console.error('Error playing audio:', error);
        }
    }

    function displayQuiz(quiz) {
        if (!quiz) return;
        
        currentQuiz = quiz;
        const quizContent = quizContainer.querySelector('.quiz-content');
        const questionEl = quizContent.querySelector('.quiz-question');
        const optionsEl = quizContent.querySelector('.quiz-options');
        const feedbackEl = quizContent.querySelector('.quiz-feedback');
        
        questionEl.textContent = quiz.question;
        optionsEl.innerHTML = '';
        feedbackEl.textContent = '';
        feedbackEl.style.display = 'none';
        
        quiz.options.forEach(option => {
            const button = document.createElement('button');
            button.className = 'quiz-option';
            button.textContent = option;
            button.onclick = () => checkAnswer(option);
            optionsEl.appendChild(button);
        });
        
        quizContainer.classList.remove('hidden');
    }

    function displayTip(tip) {
        if (!tip) return;
        const tipContent = tipContainer.querySelector('.tip-content');
        tipContent.textContent = tip;
        tipContainer.classList.remove('hidden');
    }

    async function checkAnswer(answer) {
        if (!currentQuiz) return;
        
        try {
            const response = await fetch('/check_answer', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    question: currentQuiz,
                    answer: answer
                })
            });

            const result = await response.json();
            const feedback = quizContainer.querySelector('.quiz-feedback');
            feedback.textContent = result.message;
            feedback.style.display = 'block';
            
            // Highlight correct/incorrect answers
            const options = quizContainer.querySelectorAll('.quiz-option');
            options.forEach(option => {
                if (option.textContent === answer) {
                    option.classList.add(result.correct ? 'correct' : 'incorrect');
                }
                option.disabled = true;
            });
            
            // Play sound effect
            if (soundEnabled) {
                const audio = new Audio(result.correct ? '/static/correct.mp3' : '/static/incorrect.mp3');
                audio.play().catch(err => console.error('Error playing sound:', err));
            }
        } catch (error) {
            console.error('Error checking answer:', error);
        }
    }

    function closeQuiz() {
        quizContainer.classList.add('hidden');
        currentQuiz = null;
        const feedbackEl = quizContainer.querySelector('.quiz-feedback');
        feedbackEl.textContent = '';
        feedbackEl.style.display = 'none';
    }

    async function sendMessage() {
        const message = userInput.value.trim();
        if (!message || isProcessing) return;

        isProcessing = true;
        userInput.value = '';
        addMessage(message, true);
        showLoading();

        try {
            const response = await fetch('/send_message', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message: message })
            });

            if (!response.ok) throw new Error('Failed to send message');
            
            const data = await response.json();
            hideLoading();
            
            // Add bot's response
            addMessage(data.response);
            
            // Handle speech
            if (data.speech_available && soundEnabled) {
                await playResponse(data.response);
            }
            
            // Handle quiz if present
            if (data.quiz) {
                displayQuiz(data.quiz);
            } else {
                quizContainer.classList.add('hidden');
            }
            
            // Handle tip if present
            if (data.tip) {
                displayTip(data.tip);
            } else {
                tipContainer.classList.add('hidden');
            }
        } catch (error) {
            console.error('Error:', error);
            hideLoading();
            addMessage("I'm having trouble understanding. Could you try asking that again?");
        } finally {
            isProcessing = false;
            userInput.focus();
        }
    }

    // Voice input handling
    voiceButton.addEventListener('click', async () => {
        if (!('webkitSpeechRecognition' in window)) {
            alert('Speech recognition is not supported in your browser.');
            return;
        }

        if (isProcessing) return;

        const recognition = new webkitSpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;

        recognition.onstart = () => {
            voiceButton.classList.add('recording');
            userInput.placeholder = 'Listening...';
        };

        recognition.onend = () => {
            voiceButton.classList.remove('recording');
            userInput.placeholder = 'Type your question here...';
        };

        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            userInput.value = transcript;
            sendMessage();
        };

        recognition.start();
    });

    // Toggle sound
    soundButton.addEventListener('click', () => {
        soundEnabled = !soundEnabled;
        soundButton.querySelector('i').className = soundEnabled ? 'fas fa-volume-up' : 'fas fa-volume-mute';
    });

    // Quiz generation button
    const generateQuizButton = document.getElementById('generate-quiz');
    if (generateQuizButton) {
        generateQuizButton.addEventListener('click', async () => {
            if (isProcessing) return;
            
            isProcessing = true;
            showLoading();
            
            try {
                const response = await fetch('/generate_quiz');
                if (!response.ok) throw new Error('Failed to generate quiz');
                
                const data = await response.json();
                if (data.quiz) {
                    displayQuiz(data.quiz);
                }
                if (data.tip) {
                    displayTip(data.tip);
                }
            } catch (error) {
                console.error('Error generating quiz:', error);
                addMessage("Sorry, I couldn't generate a quiz right now. Please try again!");
            } finally {
                hideLoading();
                isProcessing = false;
            }
        });
    }

    // Close quiz button
    if (closeQuizButton) {
        closeQuizButton.addEventListener('click', closeQuiz);
    }

    // Send message on button click
    sendButton.addEventListener('click', sendMessage);

    // Send message on Enter key (without Shift)
    userInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // Focus input on page load
    userInput.focus();
});
