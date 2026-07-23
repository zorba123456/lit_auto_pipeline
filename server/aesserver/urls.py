"""URL configuration for aesserver project."""
from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('reader.urls')),
    path('dashboard', views.index, name='index'),
    path('api/status', views.api_status, name='api_status'),
]
