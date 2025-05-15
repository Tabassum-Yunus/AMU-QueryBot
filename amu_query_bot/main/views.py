from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from .models import Feedback
import json

# Create your views here.

def home(request):
    return render(request, 'index.html')

def about(request):
    return render(request, 'about.html')

@login_required(login_url='login')
def submit_feedback(request):
    if request.method == 'POST':
        try:
            rating = int(request.POST.get('rating'))
            comments = request.POST.get('comments', '')
            
            if rating < 1 or rating > 5:
                messages.error(request, "Rating must be between 1 and 5.")
                return redirect('home')
            
            Feedback.objects.create(
                user=request.user,
                rating=rating,
                comments=comments
            )
            
            messages.success(request, "Thank you for your feedback! We appreciate your input.")
            return redirect('home')
            
        except (ValueError, TypeError):
            messages.error(request, "Invalid rating value. Please try again.")
        except Exception as e:
            messages.error(request, "An error occurred while submitting your feedback. Please try again.")
        
        return redirect('home')
    
    context = {
        'rating_choices': Feedback.RATING_CHOICES
    }
    return render(request, 'feedback.html', context)