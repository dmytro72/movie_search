from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from movies.models import Film, Actor, FilmActor
from movies.utils import normalize


class ViewTestCase(TestCase):
    def setUp(self):
        """Setup test data"""
        self.client = Client()
        
        # Create test films
        self.film1 = Film.objects.create(
            title="Forrest Gump",
            url="https://example.com/forrest-gump"
        )
        
        self.film2 = Film.objects.create(
            title="The Shawshank Redemption",
            url="https://example.com/shawshank"
        )
        
        # Create test actors
        self.actor1 = Actor.objects.create(
            name="Tom Hanks",
            url="https://example.com/tom-hanks"
        )
        
        self.actor2 = Actor.objects.create(
            name="Morgan Freeman",
            url="https://example.com/morgan-freeman"
        )
        
        # Link actors to films
        FilmActor.objects.create(film=self.film1, actor=self.actor1)
        FilmActor.objects.create(film=self.film2, actor=self.actor2)
    
    def test_search_view_get(self):
        """Test GET request to the search page"""
        response = self.client.get(reverse('movies:search'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Hledání v Top 300 filmech')
    
    def test_search_view_with_query(self):
        """Test search with a query"""
        response = self.client.get(reverse('movies:search'), {'q': 'forrest'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Forrest Gump')
    
    def test_search_view_case_insensitive(self):
        """Test case-insensitive search"""
        response = self.client.get(reverse('movies:search'), {'q': 'FORREST'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Forrest Gump')
    
    def test_search_view_partial_match(self):
        """Test partial match search"""
        response = self.client.get(reverse('movies:search'), {'q': 'shaw'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'The Shawshank Redemption')
    
    def test_search_actors(self):
        """Test searching for actors"""
        response = self.client.get(reverse('movies:search'), {'q': 'tom'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Tom Hanks')
    
    def test_film_detail_view(self):
        """Test film detail page"""
        response = self.client.get(
            reverse('movies:film_detail', args=[self.film1.id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Forrest Gump')
        self.assertContains(response, 'Tom Hanks')
    
    def test_actor_detail_view(self):
        """Test actor detail page"""
        response = self.client.get(
            reverse('movies:actor_detail', args=[self.actor1.id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Tom Hanks')
        self.assertContains(response, 'Forrest Gump')
    
    def test_film_detail_404(self):
        """Test 404 for non-existent film"""
        response = self.client.get(
            reverse('movies:film_detail', args=[9999])
        )
        self.assertEqual(response.status_code, 404)
    
    def test_actor_detail_404(self):
        """Test 404 for non-existent actor"""
        response = self.client.get(
            reverse('movies:actor_detail', args=[9999])
        )
        self.assertEqual(response.status_code, 404)
    
    def test_search_api_view(self):
        """Test API search endpoint"""
        response = self.client.get(
            reverse('movies:search_api'), 
            {'q': 'forrest'}
        )
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn('films', data)
        self.assertIn('actors', data)
        self.assertTrue(len(data['films']) > 0)
    
    def test_search_api_empty_query(self):
        """Test API with empty query"""
        response = self.client.get(reverse('movies:search_api'))
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data['films'], [])
        self.assertEqual(data['actors'], [])


class ModelTestCase(TestCase):
    def test_film_normalization(self):
        """Test film title normalization"""
        film = Film.objects.create(
            title="Příběh Hračky",
            url="https://example.com/toy-story"
        )
        self.assertIsNotNone(film.title_normalized)
    
    def test_actor_normalization(self):
        """Test actor name normalization"""
        actor = Actor.objects.create(
            name="Václav Havel",
            url="https://example.com/vaclav-havel"
        )
        self.assertIsNotNone(actor.name_normalized)
    
    def test_movie_actor_relationship(self):
        """Test many-to-many relationship through intermediary model"""
        film = Film.objects.create(
            title="Test Film",
            url="https://example.com/test"
        )
        actor = Actor.objects.create(
            name="Test Actor",
            url="https://example.com/test-actor"
        )
        
        FilmActor.objects.create(film=film, actor=actor)
        
        self.assertIn(actor, film.actors.all())
        self.assertIn(film, actor.films.all())
