from django import forms
from django.contrib.auth import authenticate
from django.core import validators
from django.contrib.auth.forms import BaseUserCreationForm
from users import models
from django.contrib.auth import get_user_model


class UserAuthForm(forms.Form):

    email = forms.EmailField(widget=forms.EmailInput(attrs={"class": "form-control"}), help_text="Enter email here", template_name = 'field.html')
    password = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-control"}), validators=[validators.MinLengthValidator(2), validators.MaxLengthValidator(14)])

    template_name = "form.html"

    def clean_email(self):
        email = self.cleaned_data.get('email')
        return email.lower()
    
    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        password = cleaned_data.get('password')

        if email and password:
            self.user = authenticate(username=email, password=password)  # Django uses username parameter even for email auth
            if not self.user:
                raise forms.ValidationError('Invalid email or password')
        return cleaned_data
        
    def get_user(self):
        return getattr(self, 'user', None)
    
class UserSignupForm(BaseUserCreationForm):
    
    class Meta:
        # model = models.User # get_user_model
        model = get_user_model()
        fields = ("email", "first_name", "last_name", "dob" )
        # exclude = ("last_login", "password", "date_joined")

        widgets = {
            'dob': forms.DateInput(attrs={"type": "date"})
        }

class UserUpdateForm(forms.ModelForm):

    class Meta:

        model = models.User
        fields = ("first_name", "last_name")
        