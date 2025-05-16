from django.contrib import admin
from django.urls import include, path
from users import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('update/', views.update_account, name='update_account'),
]