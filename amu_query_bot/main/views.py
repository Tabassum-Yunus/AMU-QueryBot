from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_http_methods
from .models import Feedback, Resource
import json
import pandas as pd
import os

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

@user_passes_test(lambda u: u.is_superuser)
def crawl_resources(request):
    if request.method == 'POST':
        try:
            # Fetch all resources from the database
            resources = Resource.objects.all()
            
            # Create a list to store resource data
            resource_data = []
            
            # Process each resource
            for resource in resources:
                resource_data.append({
                    'URL': resource.url or '',
                    'PDF Link': resource.file.url if resource.file else '',
                    'Description': resource.description or ''
                })
            
            # Create a DataFrame
            df = pd.DataFrame(resource_data)
            
            # Create media directory if it doesn't exist
            media_dir = os.path.join('media', 'exports')
            os.makedirs(media_dir, exist_ok=True)
            
            # Use fixed filename
            filename = 'resources_export.xlsx'
            filepath = os.path.join(media_dir, filename)
            
            # Save to Excel
            df.to_excel(filepath, index=False)
            
            messages.success(request, "Resources exported successfully to resources_export.xlsx")
        except Exception as e:
            messages.error(request, f"An error occurred while exporting resources: {str(e)}")
        
        return redirect('home')
    return render(request, 'crawl_resources.html')