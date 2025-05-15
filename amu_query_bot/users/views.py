from django.shortcuts import redirect, render
from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponse, HttpResponseRedirect
from . import forms
from django.views.decorators.http import require_http_methods
from users import models
from django.contrib import messages

# Create your views here.

def login_view(request):
    if request.method == "POST":
        form = forms.UserAuthForm(data=request.POST)
    
        if form.is_valid():
            login(request, form.get_user())
            messages.success(request, "Welcome back! You've been logged in successfully.")
            next = request.GET.get('next', 'home')
            return redirect(next)
        else:
            messages.error(request, "Invalid email or password. Please try again.")
            context = {
                "form": form
            }
            return render(request, "users/login.html", context)
    else:        
        context = {
            "form": forms.UserAuthForm()
        }
        return render(request, "users/login.html", context)
    
def signup(request):
    if request.method == "POST":
        form = forms.UserSignupForm(data=request.POST)
        if form.is_valid():
            login(request, form.save())
            messages.success(request, "Account created successfully! Welcome to PeaceMindAI!")
            return redirect("home")
        else:
            messages.error(request, "Please correct the errors below.")
            context = {
                "form": form
            }
            return render(request, "users/signup.html", context)
    else:
        context = {
            "form" : forms.UserSignupForm()
        }    
        return render(request, "users/signup.html", context)
    

def update_account(request):
    user = request.user

    if request.method == "POST":
        form = forms.UserUpdateForm(data=request.POST, instance=user)

        if form.is_valid():
            form.save()
            messages.success(request, "Your profile has been updated successfully!")                    
        else:
            messages.error(request, "Please correct the errors below.")
        context = {
            "form": form,
        }
        return render(request, "users/update_profile.html", context)
    else:
        context = {
            "form" : forms.UserUpdateForm(instance=user),
        }    
        return render(request, "users/update_profile.html", context)
    
@require_http_methods(["POST"])
def logout_view(request):
    if request.method == "POST":
        logout(request)
        messages.info(request, "You have been logged out successfully.")
    return redirect('home')