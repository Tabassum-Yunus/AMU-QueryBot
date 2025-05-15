from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .utils import initialize_llm, load_or_create_vector_store, get_qa_chain
from .models import ChatMessage
from django.contrib import messages
import json

# Initialize the chatbot components
llm = initialize_llm()
vector_store = load_or_create_vector_store()
qa_chain = get_qa_chain()

@login_required(login_url='login')
def lobby(request):
    # Get chat history for the user
    chat_history = ChatMessage.objects.filter(user=request.user).order_by('-timestamp')[:50]
    return render(request, 'chat/lobby.html', {'chat_history': chat_history})

@login_required(login_url='login')
def chat_message(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_message = data.get('message', '')
            
            if not user_message.strip():
                messages.warning(request, "Please enter a message.")
                return JsonResponse({
                    'status': 'error',
                    'message': 'Message cannot be empty'
                }, status=400)
            
            # Get response from the chatbot using the qa_chain
            response = qa_chain.invoke(user_message)
            
            # Save the chat message and response
            chat_message = ChatMessage.objects.create(
                user=request.user,
                query=user_message,
                response=response
            )
            
            return JsonResponse({
                'status': 'success',
                'response': response,
                'timestamp': chat_message.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            })
            
        except Exception as e:
            messages.error(request, "An error occurred while processing your message. Please try again.")
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)
            
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)