import logging
import re
from unidecode import unidecode
from django.core.cache import cache
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from movie_search.constant import (
    CACHE_TIMEOUT,
    SEARCH_PAGINATION_SIZE,
    FIRST_PAGE
)

logger = logging.getLogger('movies.utils')

# Allow only Latin letters, digits, and spaces
_safe_re = re.compile(r"[^a-z0-9 ]")
# Collapse consecutive whitespace characters into a single space
_space_re = re.compile(r"\s+")
# Replace dash-like characters with a space before transliteration
_dash_re = re.compile(r"[‐‑‒–—―-]+")

def normalize(text: str) -> str:
    """
    Normalize a string by removing diacritical marks and converting it to lowercase ASCII,
    and keeping only Latin letters and digits.

    Args:
        text (str): The input string to normalize.

    Retrurns:
        str: A normalized ASCII-only lowercase version of the input string,
             containing only Latin letters and digits
    """
    text_with_spaces = _dash_re.sub(" ", text)
    ascii_text = unidecode(text_with_spaces).lower()
    ascii_text = _space_re.sub(" ", ascii_text)         # normalize all whitespace to single space
    cleaned = _safe_re.sub("", ascii_text)
    return  _space_re.sub(" ", cleaned).strip()


def get_cached_or_fresh_page_with_count(normalized_query, model_class, page_number, key_prefix, field_name, display_fields):
    """
    Optimized version that caches page data and total count together to reduce DB queries.
    """
    page_cache_key = f"{key_prefix}_{normalized_query}_page_{page_number}"
    count_cache_key = f"{key_prefix}_{normalized_query}_count"
    
    # Try to get both from cache
    cached_page = cache.get(page_cache_key)
    cached_count = cache.get(count_cache_key)
    
    if cached_page and cached_count is not None:
        logger.info(f"[Cache hit] {page_cache_key} and count")
        return {
            'page_data': cached_page,
            'total_count': cached_count
        }

    logger.info(f"[Cache miss] {page_cache_key} — querying database with count")

    # Create base queryset
    base_queryset = model_class.objects.filter(
        **{f"{field_name}__icontains": normalized_query}
    ).order_by(field_name)
    
    # Get count efficiently
    total_count = base_queryset.count()
    
    # Get page data
    display_queryset = base_queryset.only(*display_fields)
    paginator = Paginator(display_queryset, SEARCH_PAGINATION_SIZE)
    
    try:
        page = paginator.page(page_number)
    except PageNotAnInteger:
        page = paginator.page(FIRST_PAGE)
    except EmptyPage:
        page = paginator.page(paginator.num_pages)

    serialized = list(page.object_list.values(*display_fields))
    page_data = {
        'object_list': serialized,
        'number': page.number,
        'has_next': page.has_next(),
        'has_previous': page.has_previous(),
        'num_pages': paginator.num_pages,
    }

    # Cache both page and count
    cache.set(page_cache_key, page_data, timeout=CACHE_TIMEOUT)
    cache.set(count_cache_key, total_count, timeout=CACHE_TIMEOUT)
    
    return {
        'page_data': page_data,
        'total_count': total_count
    }


def get_cached_or_query_object(cache_key, logger_prefix, fetch_func):
    """
    Retrieve data from cach if available; otherwise, fetch it using provided function.
    """
    logger.info(f"{logger_prefix} checking cache for key: {cache_key}")
    cached = cache.get(cache_key)

    if cached:
        logger.info(f"{logger_prefix} found in cache.")
        return cached
    
    logger.info(f"{logger_prefix} not found in cache. Fetching from DB...")
    data = fetch_func()
    cache.set(cache_key, data, timeout=CACHE_TIMEOUT)
    return data


def fetch_film_data(film_id):    
    """
    Retrieve film data and its associated actors from the DB.

    Args:
        film_id (int): The primary key of the film to retrieve.

    Returns:
        dict: A dictionary containing film details and a list of actors with their IDs and names.
    """
    from .models import Film, Actor
    film = get_object_or_404(
        Film.objects.prefetch_related(
            Prefetch('actors', queryset=Actor.objects.order_by('name'), to_attr='actors_sorted')
        ),
        id= film_id
    )
    logger.debug(f"Fetched film '{film.title}' (ID: {film_id})")
    return {
        'film': {
            'title':film.title,
            'url': film.url,
        },
        'actors': [{
            'id': actor.id,
            'name': actor.name
        } for actor in film.actors_sorted]
    }


def fetch_actor_data(actor_id):
    """
    Retrieve actor data and the films they participated in from the DB.

    Args:
        actor_id (int): The primary key of the actor to retrieve.

    Returns:
        dict: A dictionary containing actor details and a list of films with their IDs and titles.
    """
    from .models import Film, Actor
    actor = get_object_or_404(
        Actor.objects.prefetch_related(
            Prefetch('films', queryset=Film.objects.order_by('title'), to_attr='films_sorted')
        ),
        id = actor_id
    )
    logger.debug(f"Fetched actor '{actor.name}' (ID: {actor_id})")
    return {
        'actor': {
            'name': actor.name,
            'url': actor.url,
        },
        'films': [{
            'id': film.id,
            'title': film.title,
        } for film in actor.films_sorted]
    }


class SimplePage:
    def __init__(self, object_list, number, has_next, has_previous, num_pages):
        self.object_list = object_list
        self.number = number
        self.has_next = has_next
        self.has_previous = has_previous
        self.paginator = self
        self.num_pages = num_pages
        self.page_range = range(1, num_pages + 1)

    def __iter__(self):
        return iter(self.object_list)