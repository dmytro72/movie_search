import logging
from django.shortcuts import render
from django.http import JsonResponse
from .models import Film, Actor
from .utils import (
    normalize,
    get_cached_or_fresh_results,
    paginate_results,
    get_cached_or_query_object,
    fetch_film_data,
    fetch_actor_data,
)
from movie_search.constant import API_LIMIT

logger = logging.getLogger('movies.views')


def search_view(request):
    """
    Screen 1: Search for films and actors
    """
    query = request.GET.get('q', '').strip()

    films = []
    actors = []
    films_page = None
    actors_page = None

    if query:
        normalized_query = normalize(query)
        films, actors = get_cached_or_fresh_results(normalized_query)

        logger.info(f"Found {len(films)} films and {len(actors)} actors for query '{query}'")

        films_page = paginate_results(request, films, 'film_page', 'Films')
        actors_page = paginate_results(request, actors, 'actor_page', 'Actors')

    context = {
        'query': query,
        'films': films_page,
        'actors': actors_page,
        'films_count': len(films),
        'actors_count': len(actors),
    }

    logger.info("Search results rendered successfully")
    return render(request, 'movies/search.html', context)


def film_detail_view(request, film_id):
    """
    Screen 2: Film details
    """
    logger.info(f"Film detail request for film_id: {film_id}")
    cache_key = f"film_{film_id}"

    data = get_cached_or_query_object(
        cache_key,
        logger_prefix=f"Film {film_id}",
        fetch_func=lambda: fetch_film_data(film_id)
    )

    logger.debug(f"Film '{data['film']['title']}' has {len(data['actors'])} actors")
    logger.info("Film detail rendered successfully")

    return render(request, 'movies/film_detail.html', {
        'film': data['film'],
        'actors': data['actors'],
    })


def actor_detail_view(request, actor_id):
    """
    Screen 2: Actor details
    """
    logger.info(f"Actor detail request for actor_id: {actor_id}")
    cache_key = f"actor_{actor_id}"

    data = get_cached_or_query_object(
        cache_key,
        logger_prefix=f"Actor {actor_id}",
        fetch_func=lambda: fetch_actor_data(actor_id)
    )

    logger.debug(f"Actor '{data['actor']['name']}' played in {len(data['films'])} films")
    logger.info("Actor detail rendered successfully")

    return render(request, 'movies/actor_detail.html', {
        'actor': data['actor'],
        'films': data['films'],
    })


def search_api_view(request):
    """
    API endpoint for search
    """
    query = request.GET.get('q', '').strip()
    logger.info(f"API search request with query: '{query}'")
    
    if not query:
        logger.debug("Empty query received for API search")
        return JsonResponse({'films': [], 'actors': []})
    
    normalized_query = normalize(query)
    logger.debug(f"API search normalized query: '{normalized_query}'")

    films = Film.objects.filter(
        title_normalized__icontains=normalized_query
    ).values('id', 'title')[:API_LIMIT]

    actors = Actor.objects.filter(
        name_normalized__icontains=normalized_query
    ).values('id', 'name')[:API_LIMIT]

    logger.info("API search returned results")
    
    return JsonResponse({
        'films': list(films),
        'actors': list(actors),
        'limit_reached': len(films) == API_LIMIT or len(actors) == API_LIMIT,
    })