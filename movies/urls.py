from django.urls import path
from . import views

app_name = 'movies'

urlpatterns = [
    # screen 1: search for films and actors
    path('', views.search_view, name='search'),
    path('search/', views.search_view, name='search'),

    # Screen 2: Details
    path('film/<int:film_id>/', views.film_detail_view, name='film_detail'),
    path('actor/<int:actor_id>/', views.actor_detail_view, name='actor_detail'),
    
    # API endpoints (optional)
    path('api/search/', views.search_api_view, name='search_api'),
]