import logging
from django.shortcuts import render, get_object_or_404
from django.db.models import Prefetch
from django.http import JsonResponse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.cache import cache
from .models import Film, Actor
from .utils import normalize

logger = logging.getLogger('movies.views')

SEARCH_PAGINATION_SIZE = 25
API_LIMIT = 50
FIRST_PAGE = 1


def search_view(request):
    """
    Screen 1: Search for films and actors
    """
    query = request.GET.get('q', '').strip()
    logger.info(f"Search request received with query: '{query}'")

    films = []
    actors = []
    films_page = None
    actors_page = None

    if query:
        normalized_query = normalize(query)
        logger.debug(f"Normalized query: '{normalized_query}'")

        cache_key = f"search_{normalized_query}"
        cached_data = cache.get(cache_key)

        if cached_data:
            logger.info(f"Found cached data in cache with key: '{cache_key}'")
            films = cached_data['films']
            actors = cached_data['actors']
        else:
            logger.info("No cached data found in cache. Fetching data from DB...")
            films_qs = Film.objects.filter(
                title_normalized__icontains=normalized_query
            ).order_by('title').values('id','title', 'url')

            actors_qs = Actor.objects.filter(
                name_normalized__icontains=normalized_query
            ).order_by('name').values('id', 'name', 'url')

            films = list(films_qs)
            actors = list(actors_qs)

            cache.set(cache_key, {'films':films, 'actors':actors}, timeout=60*60*24) # 24 hours

        films_count = len(films)
        actors_count = len(actors)
        logger.info(f"Found {films_count} films and {actors_count} actors for query '{query}'")

        film_paginator = Paginator(films, SEARCH_PAGINATION_SIZE)
        actor_paginator = Paginator(actors, SEARCH_PAGINATION_SIZE)

        film_page_number = request.GET.get('film_page')
        actor_page_number = request.GET.get('actor_page')

        try:
            films_page = film_paginator.get_page(film_page_number)
            logger.debug(f"Films page {film_page_number or 1} requested")
        except PageNotAnInteger:
            films_page = film_paginator.page(FIRST_PAGE)
            logger.warning(f"Invalid page number: '{film_page_number}', using first page")
        except EmptyPage:
            films_page = film_paginator.page(film_paginator.num_pages)
            logger.warning(f"Film page {film_page_number}' is empty, using last page")

        try:
            actors_page = actor_paginator.get_page(actor_page_number)
            logger.debug(f"Actors page {actor_page_number or 1} requested")
        except PageNotAnInteger:
            actors_page = actor_paginator.page(FIRST_PAGE)
            logger.warning(f"Invalid actor page number: {actor_page_number}, using page 1")
        except EmptyPage:
            actors_page = actor_paginator.page(actor_paginator.num_pages)
            logger.warning(f"Actor page {actor_page_number} is empty, using last page")

    context = {
        'query': query,
        'films': films_page,
        'actors': actors_page,
        'films_count': len(films) if films else 0,
        'actors_count': len(actors) if actors else 0,
    }

    logger.info("Search results rendered successfully")
    return render(request, 'movies/search.html', context)


def film_detail_view(request, film_id):
    """
    Screen 2: Film details
    """
    logger.info(f"Film detail request for film_id: {film_id}")

    cache_key = f"film_{film_id}"
    cached_data = cache.get(cache_key)

    if cached_data:
        logger.info(f"Found cached film: {film_id}")
        film_data = cached_data['film']
        actors_data = cached_data['actors']
    else:
        logger.info(f"Fetching film from database: {film_id}")
        film = get_object_or_404(
            Film.objects.prefetch_related(
                Prefetch('actors', queryset=Actor.objects.order_by('name'), to_attr='actors_sorted')
                ),
            id=film_id
        )    
        logger.debug(f"Found film: '{film.title}' (ID: {film_id})")

        film_data = {
            'title': film.title,
            'url': film.url,
        }
        actors_data = [{'id': actor.id, 'name': actor.name} for actor in film.actors_sorted]

        cache.set(cache_key, {'film': film_data, 'actors': actors_data}, timeout=60*60*24) # 24 hours

    actors_count = len(actors_data)
    logger.debug(f"Film '{film_data['title']}' has {actors_count} actors")

    context = {
        'film': film_data,
        'actors': actors_data,
    }

    logger.info("Film detail rendered successfully")
    return render(request, 'movies/film_detail.html', context)


def actor_detail_view(request, actor_id):
    """
    Screen 2: Actor details
    """
    logger.info(f"Actor detail request for actor_id: {actor_id}")

    cache_key = f"actor_{actor_id}"
    cached_data = cache.get(cache_key)
    
    if cached_data:
        logger.info(f"Found cached data for actor: {actor_id}")
        actor_data = cached_data['actor']
        films_data = cached_data['films']
    else:
        logger.info(f"Fetching actor from db: {actor_id}")
        actor = get_object_or_404(
            Actor.objects.prefetch_related(
                Prefetch('films', queryset=Film.objects.order_by('title'), to_attr='films_sorted')
            ),
            id=actor_id
        )
        logger.debug(f"Found actor: '{actor.name}' (ID: {actor_id})")

        actor_data = {
            'name': actor.name,
            'url': actor.url,
        }
        films_data = [{'id': film.id, 'title': film.title} for film in actor.films_sorted]

        cache.set(cache_key, {'actor': actor_data, 'films': films_data}, timeout=60*60*24) # 24 hours

    films_count = len(films_data)
    logger.debug(f"Actor '{actor_data['name']}' played in {films_count} films")

    context = {
        'actor': actor_data,
        'films': films_data,
    }

    logger.info("Actor detail rendered successfully")
    return render(request, 'movies/actor_detail.html', context)


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