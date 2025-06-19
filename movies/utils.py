import logging
import re
from unidecode import unidecode
from django.core.cache import cache
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage

logger = logging.getLogger('movies.utils')

CACHE_TIMEOUT = 60 * 60 * 24 # 24 hours
SEARCH_PAGINATION_SIZE = 25
FIRST_PAGE = 1

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


def get_cached_or_fresh_results(normalized_query):
    """
    Retrieve search results for films and actors by a normalized query string, 
    using cache if available, otherwise querying the database.    
    """
    from .models import Film, Actor
    cache_key = f"search_{normalized_query}"
    cached = cache.get(cache_key)
    if cached:
        logger.info(f"Found cached data for key: '{cache_key}")
        return cached['films'], cached['actors']
    
    logger.info("No cached data found. Fetching from DB...")
    films = list(Film.objects.filter(
        title_normalized__icontains=normalized_query
    ).order_by('title').values('id', 'title', 'url'))

    actors = list(Actor.objects.filter(
        name_normalized__icontains=normalized_query
    ).order_by('name').values('id', 'name', 'url'))

    cache.set(cache_key, {'films': films, 'actors': actors}, timeout=CACHE_TIMEOUT)
    return films, actors


def paginate_results(request, items, param_name, label):
    """
    Paginate a list or queryset of items based on a page number from the request.

    Args:
        request (HttpRequest): The Django HTTP request object containing GET parameters.
        items (list or QuerySet): The collection of items to paginate.
        param_name (str): The name of the GET parameter used to specify the page number.
        label (str): A descriptive label for the items being paginated (used in logging).

    Returns:
        Page: A Django Paginator Page object corresponding to the requested page.
    """
    page_number = request.GET.get(param_name)
    paginator = Paginator(items, SEARCH_PAGINATION_SIZE)
    try:
        page = paginator.get_page(page_number)
        logger.debug(f"{label} page {page_number or 1} requested")
    except PageNotAnInteger:
        page = paginator.page(FIRST_PAGE)
        logger.warning(f"Invalid {label.lower()} page number: '{page_number}', using first page")
    except EmptyPage:
        page = paginator.page(paginator.num_pages)
        logger.warning(f"{label} page '{page_number}' is empty, using last page")
    return page