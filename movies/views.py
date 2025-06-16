from django.shortcuts import render, get_object_or_404
from django.db.models import Q
from django.http import JsonResponse
from django.core.paginator import Paginator
from .models import Film, Actor
from .utils import normalize


def search_view(request):
    """
    Screen 1: Search for films and actors
    """
    query = request.GET.get('q', '').strip()
    films = []
    actors = []

    if query:
        normalized_query = normalize(query)
        films = Film.objects.filter(
            title_normalized__icontains=normalized_query
            ).order_by('title')
        
        actors = Actor.objects.filter(
            name_normalized__icontains=normalized_query
            ).order_by('name')
        
    context = {
        'query': query,
        'films': films,
        'actors': actors,
        'films_count': films.count() if films else 0,
        'actors_count': actors.count() if actors else 0,
    }

    return render(request, 'movies/search.html', context)


def film_detail_view(request, film_id):
    """
    Screen 2: Film details
    """
    film = get_object_or_404(Film, id=film_id)
    actors = film.actors.all().order_by('name')

    context = {
        'film': film,
        'actors': actors,
    }

    return render(request, 'movies/film_detail.html', context)


def actor_detail_view(request, actor_id):
    """
    Screen 2: Actor details
    """
    actor = get_object_or_404(Actor, id=actor_id)
    films = actor.films.all().order_by('title')

    print(f"Films for actor {actor.name}: {films}")

    context = {
        'actor': actor,
        'films': films,
    }

    return render(request, 'movies/actor_detail.html', context)


# API endpoints (optional)
def search_api_view(request):
    """
    API endpoint for search
    """
    query = request.GET.get('q', '').strip()
    
    if not query:
        return JsonResponse({'films': [], 'actors': []})
    
    normalized_query = normalize(query)

    films = Film.objects.filter(
        title_normalized__icontains=normalized_query
    ).values('id', 'title')[:50]

    actors = Actor.objects.filter(
        name_normalized__icontains=normalized_query
    ).values('id', 'name')[:50]
    
    return JsonResponse({
        'films': list(films),
        'actors': list(actors),
    })