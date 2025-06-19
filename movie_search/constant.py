SEARCH_PAGINATION_SIZE = 25
API_LIMIT = 50
FIRST_PAGE = 1
CACHE_TIMEOUT = 60 * 60 * 24 # 24 hours
SEARCH_PAGINATION_SIZE = 25

# parsing settings
DEFAULT_MOVIE_LIMIT = 300
MOVIES_PER_CSFD_PAGE = 100
MIN_REQUEST_DELAY = 1  # in seconds
MAX_REQUEST_DELAY = 3  # in seconds

CSFD_BASE_URL = "https://www.csfd.cz"
CSFD_TOP_MOVIES_URL = "https://www.csfd.cz/zebricky/filmy/nejlepsi/"

MOVIE_SELECTOR = "header.article-header h3.film-title-norating a.film-title-name"
ACTOR_URL_PATTERN = r'/tvurce/\d+'
CAST_HEADER_PATTERN = r'Hrají:'

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
ACCEPT_LANGUAGE = "cs,en;q=0.9"