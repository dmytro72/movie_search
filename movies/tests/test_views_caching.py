import pytest
from django.urls import reverse
from django.core.cache import cache
from unittest.mock import patch
from movies.models import Film, Actor, FilmActor
from movies.utils import normalize


@pytest.fixture
def test_data():
    """Create test data for caching tests"""
    # Create test films
    film1 = Film.objects.create(
        title="Forrest Gump",
        url="https://example.com/forrest-gump"
    )
    
    film2 = Film.objects.create(
        title="The Shawshank Redemption", 
        url="https://example.com/shawshank"
    )
    
    # Create test actors
    actor1 = Actor.objects.create(
        name="Tom Hanks",
        url="https://example.com/tom-hanks"
    )
    
    actor2 = Actor.objects.create(
        name="Morgan Freeman",
        url="https://example.com/morgan-freeman"
    )
    
    # Link actors to films
    FilmActor.objects.create(film=film1, actor=actor1)
    FilmActor.objects.create(film=film2, actor=actor2)
    
    return {
        'film1': film1,
        'film2': film2,
        'actor1': actor1,
        'actor2': actor2,
    }


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear cache before and after each test"""
    cache.clear()
    yield
    cache.clear()


# ========== SEARCH CACHING TESTS ==========

@pytest.mark.django_db
def test_search_cache_miss_and_hit(client, test_data):
    """Test search cache miss on first request and hit on second"""
    query = 'forrest'
    
    # First request - should be cache miss
    with patch('movies.utils.logger') as mock_logger:
        response1 = client.get(reverse('movies:search'), {'q': query})
        
        # Verify cache miss was logged
        mock_logger.info.assert_any_call("No cached data found. Fetching from DB...")
    
    assert response1.status_code == 200
    assert 'Forrest Gump' in response1.content.decode()
    
    # Verify cache was set
    cache_key = f"search_{normalize(query)}"
    cached_data = cache.get(cache_key)
    assert cached_data is not None
    assert 'films' in cached_data
    assert 'actors' in cached_data
    
    # Second request - should be cache hit
    with patch('movies.utils.logger') as mock_logger:
        response2 = client.get(reverse('movies:search'), {'q': query})
        
        # Verify cache hit was logged
        mock_logger.info.assert_any_call(f"Found cached data for key: '{cache_key}")
    
    assert response2.status_code == 200
    assert 'Forrest Gump' in response2.content.decode()


@pytest.mark.django_db
def test_search_cache_different_queries(client, test_data):
    """Test that different queries create different cache entries"""
    query1 = 'forrest'
    query2 = 'shawshank'
    
    # Make requests with different queries
    client.get(reverse('movies:search'), {'q': query1})
    client.get(reverse('movies:search'), {'q': query2})
    
    # Verify both cache entries exist
    cache_key1 = f"search_{normalize(query1)}"
    cache_key2 = f"search_{normalize(query2)}"
    
    assert cache.get(cache_key1) is not None
    assert cache.get(cache_key2) is not None
    
    # Verify cache contents are different
    cached_data1 = cache.get(cache_key1)
    cached_data2 = cache.get(cache_key2)
    assert cached_data1 != cached_data2


@pytest.mark.django_db
def test_search_cache_normalization(client, test_data):
    """Test that query normalization works correctly for caching"""
    # These should all use the same cache key due to normalization
    queries = ['FORREST', 'forrest', 'Forrest', 'fOrReSt']
    
    # Make first request
    client.get(reverse('movies:search'), {'q': queries[0]})
    
    cache_key = f"search_{normalize(queries[0])}"
    
    # Verify all normalized queries would use the same cache key
    for query in queries:
        normalized = normalize(query)
        expected_key = f"search_{normalized}"
        assert cache_key == expected_key


@pytest.mark.django_db
def test_search_cache_timeout(client, test_data):
    """Test search cache timeout setting"""
    query = 'forrest'
    
    with patch('django.core.cache.cache.set') as mock_cache_set:
        client.get(reverse('movies:search'), {'q': query})
        
        # Verify cache.set was called with 24 hour timeout
        mock_cache_set.assert_called_once()
        args, kwargs = mock_cache_set.call_args
        assert kwargs['timeout'] == 60*60*24  # 24 hours


# ========== FILM DETAIL CACHING TESTS ==========

@pytest.mark.django_db
def test_film_detail_cache_miss_and_hit(client, test_data):
    """Test film detail cache miss on first request and hit on second"""
    film_id = test_data['film1'].id
    
    # First request - should be cache miss
    with patch('movies.views.logger') as mock_logger:
        response1 = client.get(reverse('movies:film_detail', args=[film_id]))
        
        # Verify cache miss was logged
        mock_logger.info.assert_any_call(f"Fetching film from database: {film_id}")
    
    assert response1.status_code == 200
    assert 'Forrest Gump' in response1.content.decode()
    
    # Verify cache was set
    cache_key = f"film_{film_id}"
    cached_data = cache.get(cache_key)
    assert cached_data is not None
    assert 'film' in cached_data
    assert 'actors' in cached_data
    
    # Second request - should be cache hit
    with patch('movies.views.logger') as mock_logger:
        response2 = client.get(reverse('movies:film_detail', args=[film_id]))
        
        # Verify cache hit was logged
        mock_logger.info.assert_any_call(f"Found cached film: {film_id}")
    
    assert response2.status_code == 200
    assert 'Forrest Gump' in response2.content.decode()


@pytest.mark.django_db
def test_film_detail_cache_structure(client, test_data):
    """Test film detail cache data structure"""
    film_id = test_data['film1'].id
    
    # Make request to populate cache
    client.get(reverse('movies:film_detail', args=[film_id]))
    
    # Check cache structure
    cache_key = f"film_{film_id}"
    cached_data = cache.get(cache_key)
    
    assert cached_data is not None
    assert 'film' in cached_data
    assert 'actors' in cached_data
    
    # Check film data structure
    film_data = cached_data['film']
    assert 'title' in film_data
    assert 'url' in film_data
    assert film_data['title'] == 'Forrest Gump'
    
    # Check actors data structure
    actors_data = cached_data['actors']
    assert isinstance(actors_data, list)
    if actors_data:  # If there are actors
        assert 'id' in actors_data[0]
        assert 'name' in actors_data[0]


@pytest.mark.django_db
def test_film_detail_cache_timeout(client, test_data):
    """Test film detail cache timeout setting"""
    film_id = test_data['film1'].id
    
    with patch('django.core.cache.cache.set') as mock_cache_set:
        client.get(reverse('movies:film_detail', args=[film_id]))
        
        # Verify cache.set was called with 24 hour timeout
        mock_cache_set.assert_called_once()
        args, kwargs = mock_cache_set.call_args
        assert kwargs['timeout'] == 60*60*24  # 24 hours


# ========== ACTOR DETAIL CACHING TESTS ==========

@pytest.mark.django_db
def test_actor_detail_cache_miss_and_hit(client, test_data):
    """Test actor detail cache miss on first request and hit on second"""
    actor_id = test_data['actor1'].id
    
    # First request - should be cache miss
    with patch('movies.views.logger') as mock_logger:
        response1 = client.get(reverse('movies:actor_detail', args=[actor_id]))
        
        # Verify cache miss was logged
        mock_logger.info.assert_any_call(f"Fetching actor from db: {actor_id}")
    
    assert response1.status_code == 200
    assert 'Tom Hanks' in response1.content.decode()
    
    # Verify cache was set
    cache_key = f"actor_{actor_id}"
    cached_data = cache.get(cache_key)
    assert cached_data is not None
    assert 'actor' in cached_data
    assert 'films' in cached_data
    
    # Second request - should be cache hit
    with patch('movies.views.logger') as mock_logger:
        response2 = client.get(reverse('movies:actor_detail', args=[actor_id]))
        
        # Verify cache hit was logged
        mock_logger.info.assert_any_call(f"Found cached data for actor: {actor_id}")
    
    assert response2.status_code == 200
    assert 'Tom Hanks' in response2.content.decode()


@pytest.mark.django_db
def test_actor_detail_cache_structure(client, test_data):
    """Test actor detail cache data structure"""
    actor_id = test_data['actor1'].id
    
    # Make request to populate cache
    client.get(reverse('movies:actor_detail', args=[actor_id]))
    
    # Check cache structure
    cache_key = f"actor_{actor_id}"
    cached_data = cache.get(cache_key)
    
    assert cached_data is not None
    assert 'actor' in cached_data
    assert 'films' in cached_data
    
    # Check actor data structure
    actor_data = cached_data['actor']
    assert 'name' in actor_data
    assert 'url' in actor_data
    assert actor_data['name'] == 'Tom Hanks'
    
    # Check films data structure
    films_data = cached_data['films']
    assert isinstance(films_data, list)
    if films_data:  # If there are films
        assert 'id' in films_data[0]
        assert 'title' in films_data[0]


@pytest.mark.django_db
def test_actor_detail_cache_timeout(client, test_data):
    """Test actor detail cache timeout setting"""
    actor_id = test_data['actor1'].id
    
    with patch('django.core.cache.cache.set') as mock_cache_set:
        client.get(reverse('movies:actor_detail', args=[actor_id]))
        
        # Verify cache.set was called with 24 hour timeout
        mock_cache_set.assert_called_once()
        args, kwargs = mock_cache_set.call_args
        assert kwargs['timeout'] == 60*60*24  # 24 hours


# ========== CACHE PERFORMANCE TESTS ==========

@pytest.mark.django_db
def test_cache_reduces_db_queries(client, test_data, django_assert_num_queries):
    """Test that caching reduces database queries"""
    query = 'forrest'
    
    # First request - should hit database
    with django_assert_num_queries(2):  # One for films, one for actors
        response1 = client.get(reverse('movies:search'), {'q': query})
        assert response1.status_code == 200
    
    # Second request - should use cache (no DB queries for search data)
    with django_assert_num_queries(0):  # No queries should be made
        response2 = client.get(reverse('movies:search'), {'q': query})
        assert response2.status_code == 200


@pytest.mark.django_db
def test_film_detail_cache_reduces_db_queries(client, test_data, django_assert_num_queries):
    """Test that film detail caching reduces database queries"""
    film_id = test_data['film1'].id
    
    # First request - should hit database
    with django_assert_num_queries(2):  # One query with prefetch_related
        response1 = client.get(reverse('movies:film_detail', args=[film_id]))
        assert response1.status_code == 200
    
    # Second request - should use cache
    with django_assert_num_queries(0):
        response2 = client.get(reverse('movies:film_detail', args=[film_id]))
        assert response2.status_code == 200


@pytest.mark.django_db
def test_actor_detail_cache_reduces_db_queries(client, test_data, django_assert_num_queries):
    """Test that actor detail caching reduces database queries"""
    actor_id = test_data['actor1'].id
    
    # First request - should hit database
    with django_assert_num_queries(2):  # One query with prefetch_related
        response1 = client.get(reverse('movies:actor_detail', args=[actor_id]))
        assert response1.status_code == 200
    
    # Second request - should use cache
    with django_assert_num_queries(0):
        response2 = client.get(reverse('movies:actor_detail', args=[actor_id]))
        assert response2.status_code == 200


# ========== CACHE INVALIDATION TESTS ==========

@pytest.mark.django_db
def test_cache_isolation_between_different_items(client, test_data):
    """Test that cache entries for different items are isolated"""
    # Cache data for different films
    film1_id = test_data['film1'].id
    film2_id = test_data['film2'].id
    
    client.get(reverse('movies:film_detail', args=[film1_id]))
    client.get(reverse('movies:film_detail', args=[film2_id]))
    
    # Verify both cache entries exist and are different
    cache_key1 = f"film_{film1_id}"
    cache_key2 = f"film_{film2_id}"
    
    cached_data1 = cache.get(cache_key1)
    cached_data2 = cache.get(cache_key2)
    
    assert cached_data1 is not None
    assert cached_data2 is not None
    assert cached_data1['film']['title'] != cached_data2['film']['title']


@pytest.mark.django_db
def test_empty_search_not_cached(client, test_data):
    """Test that empty search queries are not cached"""
    # Make request with empty query
    response = client.get(reverse('movies:search'), {'q': ''})
    assert response.status_code == 200
    
    # Verify no cache entry was created
    cache_key = f"search_{normalize('')}"
    cached_data = cache.get(cache_key)
    assert cached_data is None


@pytest.mark.django_db
def test_api_search_not_cached(client, test_data):
    """Test that API search is not cached (as expected from the code)"""
    query = 'forrest'
    
    # Make API request
    response = client.get(reverse('movies:search_api'), {'q': query})
    assert response.status_code == 200
    
    # Verify no cache entry was created for API search
    cache_key = f"search_{normalize(query)}"
    cached_data = cache.get(cache_key)
    assert cached_data is None  # API doesn't use caching


# ========== PARAMETRIZED TESTS ==========

@pytest.mark.django_db
@pytest.mark.parametrize("query,expected_films", [
    ('forrest', ['Forrest Gump']),
    ('shawshank', ['The Shawshank Redemption']),
    ('FORREST', ['Forrest Gump']),  # Case insensitive
    ('nonexistent', []),  # No results
])
def test_search_cache_with_different_queries(client, test_data, query, expected_films):
    """Test search caching with various queries"""
    # First request
    response1 = client.get(reverse('movies:search'), {'q': query})
    assert response1.status_code == 200
    
    for film in expected_films:
        assert film in response1.content.decode()
    
    # Second request should use cache
    response2 = client.get(reverse('movies:search'), {'q': query})
    assert response2.status_code == 200
    
    for film in expected_films:
        assert film in response2.content.decode()
    
    # Verify cache was used (if query is not empty)
    if query.strip():
        cache_key = f"search_{normalize(query)}"
        cached_data = cache.get(cache_key)
        assert cached_data is not None


@pytest.mark.django_db
@pytest.mark.parametrize("query,expected_actors", [
    ('tom', ['Tom Hanks']),
    ('morgan', ['Morgan Freeman']),
    ('TOM', ['Tom Hanks']),  # Case insensitive
    ('nonexistent', []),  # No results
])
def test_actor_search_cache_with_different_queries(client, test_data, query, expected_actors):
    """Test actor search caching with various queries"""
    # First request
    response1 = client.get(reverse('movies:search'), {'q': query})
    assert response1.status_code == 200
    
    for actor in expected_actors:
        assert actor in response1.content.decode()
    
    # Second request should use cache
    response2 = client.get(reverse('movies:search'), {'q': query})
    assert response2.status_code == 200
    
    for actor in expected_actors:
        assert actor in response2.content.decode()


# ========== CACHE EDGE CASES ==========

@pytest.mark.django_db
def test_cache_with_special_characters(client, test_data):
    """Test caching with special characters in queries"""
    special_queries = ['forrest!', 'tom@hanks', 'test-query', 'query with spaces']
    
    for query in special_queries:
        response = client.get(reverse('movies:search'), {'q': query})
        assert response.status_code == 200
        
        # Each query should have its own cache entry
        cache_key = f"search_{normalize(query)}"
        # Note: This might be None if no results, but should not cause errors


@pytest.mark.django_db
def test_concurrent_cache_access(client, test_data):
    """Test that concurrent access to cache doesn't cause issues"""
    query = 'forrest'
    film_id = test_data['film1'].id
    
    # Make multiple requests simultaneously (simulated)
    responses = []
    for _ in range(5):
        responses.append(client.get(reverse('movies:search'), {'q': query}))
        responses.append(client.get(reverse('movies:film_detail', args=[film_id])))
    
    # All responses should be successful
    for response in responses:
        assert response.status_code == 200
    
    # Cache should be properly set
    search_cache_key = f"search_{normalize(query)}"
    film_cache_key = f"film_{film_id}"
    
    assert cache.get(search_cache_key) is not None
    assert cache.get(film_cache_key) is not None