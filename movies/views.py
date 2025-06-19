import logging
from django.shortcuts import render
from django.http import JsonResponse
from .models import Film, Actor
from .utils import (
    normalize,
    get_cached_or_fresh_page_with_count,
    SimplePage,
    get_cached_or_query_object,
    fetch_film_data,
    fetch_actor_data,
)
from movie_search.constant import API_LIMIT, FIRST_PAGE

logger = logging.getLogger('movies.views')


def search_view(request):
    """
    Screen 1: Search for films and actors with per-page caching.
    """
    query = request.GET.get('q', '').strip()

    films_page = None
    actors_page = None
    films_count = 0
    actors_count = 0

    if query:
        normalized_query = normalize(query)

        film_page_num = request.GET.get('film_page', FIRST_PAGE)
        actor_page_num = request.GET.get('actor_page', FIRST_PAGE)

        # Get films page data with count in one go
        films_data = get_cached_or_fresh_page_with_count(
            normalized_query, Film, film_page_num, 'films', 'title_normalized', ['id', 'title', 'url']
        )
        
        # Get actors page data with count in one go
        actors_data = get_cached_or_fresh_page_with_count(
            normalized_query, Actor, actor_page_num, 'actors', 'name_normalized', ['id', 'name', 'url']
        )

        films_page = SimplePage(**films_data['page_data'])
        actors_page = SimplePage(**actors_data['page_data'])
        films_count = films_data['total_count']
        actors_count = actors_data['total_count']

        logger.info(f"Search for '{query}': {films_count} films, {actors_count} actors")

    context = {
        'query': query,
        'films': films_page,
        'actors': actors_page,
        'films_count': films_count,
        'actors_count': actors_count,
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