document.addEventListener('DOMContentLoaded', () => {
    const chatMessages = document.getElementById('chat-messages');
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-button');
    const quizButton = document.getElementById('quiz-button'); // Add this line
    const voiceButton = document.getElementById('voice-input');
    const quizContainer = document.getElementById('quiz-container');
    const tipContainer = document.getElementById('tip-container');
    const loadingElement = document.getElementById('loading');
    
    let currentQuiz = null;
    let currentQuestionIndex = 0;
    let quizScore = 0;
    let isProcessing = false;

    function addMessage(message, isUser = false) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message');
        messageDiv.classList.add(isUser ? 'user-message' : 'bot-message');

        const contentDiv = document.createElement('div');
        contentDiv.classList.add('message-content');
        contentDiv.innerHTML = message;

        messageDiv.appendChild(contentDiv);
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function showLoading() {
        loadingElement.classList.remove('hidden');
    }

    function hideLoading() {
        loadingElement.classList.add('hidden');
    }

    function displayQuiz(quiz) {
        currentQuiz = quiz;
        currentQuestionIndex = 0;
        quizScore = 0;
        
        // Create quiz container HTML
        quizContainer.innerHTML = `
            <div class="quiz-header">
                <h3>🎮 Quiz: ${quiz.topic}</h3>
                <button id="close-quiz" class="close-button">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <div class="quiz-content">
                <div class="quiz-question">${quiz.questions[0].question}</div>
                <div class="quiz-options">
                    ${quiz.questions[0].options.map((option, index) => 
                        `<button class="quiz-option" data-index="${index}">${option}</button>`
                    ).join('')}
                </div>
                <div class="quiz-feedback hidden"></div>
            </div>
        `;
        
        // Show the quiz container
        quizContainer.classList.remove('hidden');
        
        // Add event listeners to answer buttons
        const optionButtons = quizContainer.querySelectorAll('.quiz-option');
        optionButtons.forEach(button => {
            button.addEventListener('click', () => {
                const selectedIndex = parseInt(button.getAttribute('data-index'));
                checkAnswer(selectedIndex);
            });
        });
        
        // Add event listener to close button
        const closeButton = document.getElementById('close-quiz');
        closeButton.addEventListener('click', closeQuiz);
    }

    function displayTip(tip) {
        tipContainer.innerHTML = `<div class="tip-content">${tip}</div>`;
        tipContainer.classList.remove('hidden');
        
        // Hide tip after 10 seconds
        setTimeout(() => {
            tipContainer.classList.add('hidden');
        }, 10000);
    }

    async function checkAnswer(selectedIndex) {
        if (!currentQuiz) return;
        
        const question = currentQuiz.questions[currentQuestionIndex];
        const isCorrect = selectedIndex === question.correct_index;
        
        // Disable all option buttons
        const optionButtons = quizContainer.querySelectorAll('.quiz-option');
        optionButtons.forEach(button => button.disabled = true);
        
        // Highlight correct and selected answers
        optionButtons.forEach((button, index) => {
            if (index === question.correct_index) {
                button.classList.add('correct');
            } else if (index === selectedIndex && !isCorrect) {
                button.classList.add('incorrect');
            }
        });
        
        // Show feedback
        const feedbackDiv = quizContainer.querySelector('.quiz-feedback');
        feedbackDiv.innerHTML = `
            <div class="quiz-feedback-content ${isCorrect ? 'correct' : 'incorrect'}">
                <i class="fas fa-${isCorrect ? 'check' : 'times'}-circle"></i>
                <p>${isCorrect ? 'Great job!' : 'Oops, not quite.'} ${question.explanation}</p>
            </div>
        `;
        feedbackDiv.classList.remove('hidden');
        
        // Update score if correct
        if (isCorrect) {
            quizScore++;
        }
        
        // Check if this is the last question
        const isLastQuestion = currentQuestionIndex === currentQuiz.questions.length - 1;
        
        // Send result to server
        try {
            const response = await fetch('/check_answer', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    quiz_id: currentQuiz.topic,
                    question_index: currentQuestionIndex,
                    selected_answer: selectedIndex,
                    correct_answer: question.correct_index,
                    is_last_question: isLastQuestion,
                    current_score: quizScore,
                    total_questions: currentQuiz.questions.length,
                    topic: currentQuiz.topic
                })
            });
            
            const result = await response.json();
            
            // If it's the last question, show completion message
            if (isLastQuestion) {
                setTimeout(() => {
                    quizContainer.innerHTML = `
                        <div class="quiz-header">
                            <h3>🎮 Quiz Complete!</h3>
                            <button id="close-quiz" class="close-button">
                                <i class="fas fa-times"></i>
                            </button>
                        </div>
                        <div class="quiz-content">
                            <div class="quiz-completion">
                                <h3>Great job! 🎉</h3>
                                <p>You scored ${quizScore} out of ${currentQuiz.questions.length}</p>
                                <p class="xp-earned">+${result.xp_earned || quizScore * 2} XP earned!</p>
                                <button class="quiz-done-button">Done</button>
                            </div>
                        </div>
                    `;
                    
                    // Add event listeners
                    const closeButton = document.getElementById('close-quiz');
                    closeButton.addEventListener('click', closeQuiz);
                    
                    const doneButton = quizContainer.querySelector('.quiz-done-button');
                    doneButton.addEventListener('click', closeQuiz);
                    
                }, 2000);
            } else {
                // Move to next question after 2 seconds
                setTimeout(() => {
                    currentQuestionIndex++;
                    const nextQuestion = currentQuiz.questions[currentQuestionIndex];
                    
                    quizContainer.innerHTML = `
                        <div class="quiz-header">
                            <h3>🎮 Quiz: ${currentQuiz.topic}</h3>
                            <button id="close-quiz" class="close-button">
                                <i class="fas fa-times"></i>
                            </button>
                        </div>
                        <div class="quiz-content">
                            <div class="quiz-question">${nextQuestion.question}</div>
                            <div class="quiz-options">
                                ${nextQuestion.options.map((option, index) => 
                                    `<button class="quiz-option" data-index="${index}">${option}</button>`
                                ).join('')}
                            </div>
                            <div class="quiz-feedback hidden"></div>
                        </div>
                    `;
                    
                    // Add event listeners
                    const optionButtons = quizContainer.querySelectorAll('.quiz-option');
                    optionButtons.forEach(button => {
                        button.addEventListener('click', () => {
                            const selectedIndex = parseInt(button.getAttribute('data-index'));
                            checkAnswer(selectedIndex);
                        });
                    });
                    
                    const closeButton = document.getElementById('close-quiz');
                    closeButton.addEventListener('click', closeQuiz);
                    
                }, 2000);
            }
            
            // If implemented in the check_answer function when a user gets a new achievement:
            if (result.new_achievement) {
                playAchievementSound();
                showAchievementNotification(result.new_achievement);
            }
            
        } catch (error) {
            console.error('Error checking answer:', error);
        }
    }

    // Add this function for celebrating quiz completion
    function celebrateQuizCompletion(score, total) {
        // Create confetti container
        const confettiContainer = document.createElement('div');
        confettiContainer.classList.add('confetti-container');
        document.body.appendChild(confettiContainer);
        
        // Add confetti pieces
        for (let i = 0; i < 50; i++) {
            const confetti = document.createElement('div');
            confetti.classList.add('confetti');
            confetti.style.left = `${Math.random() * 100}%`;
            confetti.style.animationDelay = `${Math.random() * 3}s`;
            confetti.style.backgroundColor = `hsl(${Math.random() * 360}, 80%, 60%)`;
            confettiContainer.appendChild(confetti);
        }
        
        // Show celebration message
        const celebrationMsg = document.createElement('div');
        celebrationMsg.classList.add('celebration-message');
        
        // Determine message based on score
        let message = '';
        let emoji = '';
        
        const percentage = (score / total) * 100;
        
        if (percentage === 100) {
            message = "Perfect Score! You're Amazing!";
            emoji = "🏆";
        } else if (percentage >= 80) {
            message = "Great Job! Super Smart!";
            emoji = "🌟";
        } else if (percentage >= 60) {
            message = "Well Done! Keep Learning!";
            emoji = "👍";
        } else {
            message = "Good Try! Let's Learn More!";
            emoji = "💪";
        }
        
        celebrationMsg.innerHTML = `
            <div class="celebration-emoji">${emoji}</div>
            <h2>${message}</h2>
            <p>You got ${score} out of ${total} questions right!</p>
        `;
        
        document.body.appendChild(celebrationMsg);
        
        // Remove celebration after 5 seconds
        setTimeout(() => {
            confettiContainer.remove();
            celebrationMsg.remove();
        }, 5000);
    }

    function closeQuiz() {
        quizContainer.classList.add('hidden');
        if (currentQuiz) {
            // Celebrate if it was a completed quiz
            if (quizScore > 0) {
                celebrateQuizCompletion(quizScore, currentQuiz.questions.length);
            }
        }
        currentQuiz = null;
        quizContainer.innerHTML = '';
    }

    async function sendMessage() {
        const message = userInput.value.trim();
        if (!message || isProcessing) return;
        
        // Clear input and add user message
        userInput.value = '';
        addMessage(message, true);
        
        // Show loading animation
        isProcessing = true;
        showLoading();
        
        try {
            const response = await fetch('/send_message', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ message })
            });
            
            const data = await response.json();
            
            if (data.error) {
                addMessage('Sorry, there was an error processing your message. Please try again.', false);
                return;
            }
            
            // Add bot message
            addMessage(data.response, false);
            
            // Check if we have a tip
            if (data.tip) {
                displayTip(data.tip);
            }
            
            // Check if we have a quiz
            if (data.quiz) {
                displayQuiz(data.quiz);
            }
            
        } catch (error) {
            console.error('Error sending message:', error);
            addMessage('Sorry, there was an error connecting to the server. Please try again later.', false);
        } finally {
            isProcessing = false;
            hideLoading();
        }
    }
    
    // Add this new function to handle quiz button click
    async function generateQuiz() {
        if (isProcessing) return;
        
        isProcessing = true;
        showLoading();
        
        try {
            // Add a message from the user indicating they want a quiz
            addMessage("Can I have a quiz about what we're talking about?", true);
            
            const response = await fetch('/generate_quiz');
            const data = await response.json();
            
            if (data.error) {
                addMessage('Sorry, I could not generate a quiz right now. Please try again later.', false);
                return;
            }
            
            // Add a message from the bot
            addMessage(`Sure! I've created a quiz about ${data.topic}. Let's see what you know! 🎮`, false);
            
            // Display the quiz
            displayQuiz(data);
            
        } catch (error) {
            console.error('Error generating quiz:', error);
            addMessage('Sorry, there was an error generating the quiz. Please try again later.', false);
        } finally {
            isProcessing = false;
            hideLoading();
        }
    }
    
    // Achievement unlock sound
    function playAchievementSound() {
        const sound = new Audio('https://assets.mixkit.co/sfx/preview/mixkit-unlock-game-notification-253.mp3');
        sound.volume = 0.5;
        sound.play().catch(e => console.log('Audio playback error:', e));
    }

    function showAchievementNotification(achievement) {
        const notification = document.createElement('div');
        notification.classList.add('achievement-notification');
        
        notification.innerHTML = `
            <div class="achievement-notification-icon">
                <i class="fas ${achievement.icon}"></i>
            </div>
            <div class="achievement-notification-content">
                <h3>Achievement Unlocked!</h3>
                <p>${achievement.name}</p>
                <p class="achievement-notification-points">+${achievement.points} XP</p>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.classList.add('show');
        }, 100);
        
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => notification.remove(), 500);
        }, 5000);
    }

    // Event listeners
    sendButton.addEventListener('click', sendMessage);
    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });
    
    // Add this event listener for the quiz button
    quizButton.addEventListener('click', generateQuiz);

    // Initial welcome message
    addMessage('Hi there! 👋 I\'m Buddy, your learning friend! What would you like to learn about today? You can ask me a question, or click the "Quiz Me!" button to get a fun learning quiz!', false);
});
