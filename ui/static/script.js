document.addEventListener('DOMContentLoaded', () => {
    const chatForm = document.getElementById('chat-form');
    const chatWindow = document.getElementById('chat-window');
    const userInput = document.getElementById('user-input');
    const modelSelect = document.getElementById('model-select');

    let conversation = [];
    let isFirstMessage = true;

    const formGroup = document.querySelector('.form-wrapper');
    formGroup.classList.add('first-message-form');
    userInput.classList.add('first-message-textarea');
    const sendButton = document.querySelector('.send-button');
    sendButton.classList.add('first-message-send-button');
    modelSelect.classList.add('first-message-model-select');
    const queryTitle = document.querySelector('.query-title')
    queryTitle.classList.add('first-message-h2');


    document.getElementById('new-chat').addEventListener('click', function() {
        window.location.href = '/';
    });

    function removeFirstMessageStuff(isOldChat) {
        userInput.classList.remove('first-message-textarea');
        sendButton.classList.remove('first-message-send-button');
        modelSelect.classList.remove('first-message-model-select');
        queryTitle.classList.add('hidden');
        
        if(document.querySelector('.form-wrapper')){
            formGroup.classList.remove('first-message-form');
            const parent = formGroup.parentNode;
        
            while (formGroup.firstChild) {
                parent.insertBefore(formGroup.firstChild, formGroup);
            }
        
            parent.removeChild(formGroup);
        }
    
        isFirstMessage = false;
    }

    userInput.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' && !e.shiftKey) { // Only trigger on Enter without Shift
            e.preventDefault(); // Prevent the default behavior (adding a new line)
            chatForm.requestSubmit(); // Submit the form
        }
    });

    

    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const userMessage = userInput.value.trim();
        if (!userMessage) return;

        // Display user message
        displayMessage('user', userMessage);
        conversation.push({ role: 'user', content: userMessage });
        userInput.value = '';

        if (isFirstMessage) {
            removeFirstMessageStuff(false);
        }



        // Fetch assistant's response
        const model = modelSelect.value;
        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    model: model,
                    messages: conversation,
                }),
            });

            if (!response.ok) {
                throw new Error('Network response was not ok');
            }

            const data = await response.json();
            const assistantMessage = data.reply;

            // Display assistant message
            displayMessage('assistant', assistantMessage);
            conversation.push({ role: 'assistant', content: assistantMessage });
        } catch (error) {
            console.error('Error:', error);
            displayMessage('assistant', 'An error occurred. Please try again.');
        }
    });

    function getMessageIndex(messageElement) {
        const chatWindow = document.querySelector('.chat-window');
        const allMessages = chatWindow.querySelectorAll('.message-wrapper');
        return Array.from(allMessages).indexOf(messageElement);
    }

    function addFeedbackForm(parentElement) {
        const feedbackForm = document.createElement('div');
        feedbackForm.classList.add('feedback-form');
        feedbackForm.innerHTML = `
            <span class="thumbs-up" data-feedback="positive">👍</span>
            <span class="thumbs-down" data-feedback="negative">👎</span>
        `;
        feedbackForm.style.display = 'flex'; 
        feedbackForm.style.visibility = 'hidden'; 
        parentElement.appendChild(feedbackForm);
    
        parentElement.addEventListener('mouseenter', () => {
            feedbackForm.style.visibility = 'visible'; 
        });
        parentElement.addEventListener('mouseleave', () => {
            feedbackForm.style.visibility = 'hidden'; 
        });

        const thumbsUp = feedbackForm.querySelector('.thumbs-up');
        const thumbsDown = feedbackForm.querySelector('.thumbs-down');
    
        thumbsUp.addEventListener('click', () => {
            const messageIndex = getMessageIndex(parentElement);
            sendFeedback('positive', messageIndex);
        });
        thumbsDown.addEventListener('click', () => {
            const messageIndex = getMessageIndex(parentElement);
            sendFeedback('negative', messageIndex);
        });
    
    
    }
    function getCookieValue(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) {
            return parts.pop().split(';').shift();
        }
        return null; // Return null if the cookie is not found
    }

    function sendFeedback(feedbackType, messageIdx) {
        const chatId = getCookieValue('chat_id');
        const userId = getCookieValue('user_id');

        fetch('/feedback', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ feedback_type: feedbackType, user_id: userId, chat_id: chatId, message_idx: messageIdx }),
        })
        .then(response => response.json())
        .then(data => {
            // console.log('Feedback submitted:', data);
        })
        .catch(error => {
            console.error('Error submitting feedback:', error);
        });
    }

    function displayMessage(role, content) {
        const messageWrapper = document.createElement('div');
        messageWrapper.classList.add('message-wrapper', role);
    
        const messageElement = document.createElement('div');
        messageElement.classList.add('message', role);
        messageElement.textContent = content;
        chatWindow.appendChild(messageElement);

        messageWrapper.appendChild(messageElement);
        chatWindow.appendChild(messageWrapper);
    

        if (role === 'assistant') {
            addFeedbackForm(messageWrapper);
        }

        chatWindow.scrollTop = chatWindow.scrollHeight;
    }

    window.loadChat = async (chat_id) => {
        conversation = [];
        removeFirstMessageStuff(true);
        document.cookie = `chat_id=${chat_id}; path=/; max-age=${60 * 60 * 24 * 1};`; // 1 day

        const response = await fetch(`/get_chat/${chat_id}`);
        if (response.ok) {
            const data = await response.json();
            chatWindow.innerHTML = '';
            data.messages.forEach(msg => {
                conversation.push({ role: msg.role, content: msg.content });
                displayMessage(msg.role, msg.content);
            });
        } else {
            console.log("Failed to load chat history");
        }    
    }

});
