"""django_app URL Configuration"""
from django.contrib import admin
from django.urls import path
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

@require_http_methods(["GET"])
def health_check(request):
    """Health check endpoint"""
    return JsonResponse({
        'status': 'healthy',
        'message': 'Django app is running',
        'database': 'connected'
    })

@require_http_methods(["GET"])
def home(request):
    """Home page"""
    return JsonResponse({
        'message': 'Welcome to Django + PostgreSQL + Redis Example',
        'endpoints': {
            'health': '/health/',
            'admin': '/admin/',
        }
    })

urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', health_check, name='health'),
    path('', home, name='home'),
]
