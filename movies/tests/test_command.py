import pytest
import requests
from unittest.mock import Mock, patch
from django.core.management import call_command
from io import StringIO

from movies.models import Actor, Film, FilmActor
from movies.management.commands.load_top_movies import Command


@pytest.fixture
def command():
    """Fixture for creating a Command instance."""
    return Command()


@pytest.fixture
def mock_session():
    """Fixture for a mocked HTTP session."""
    session = Mock(spec=requests.Session)
    session.headers = {}
    return session


@pytest.fixture
def sample_movie_html():
    """HTML sample containing movie data for parser testing."""
    return """
    <div class="box-content">
        <article class="box-film">
            <header class="article-header">
                <h3 class="film-title-norating">
                    <span class="film-title-user">1.</span>
                    <a href="/film/12345-test-movie/" 
                       title="Test Movie" 
                       class="film-title-name">
                       Test Movie
                    </a>
                    <span class="film-title-info">
                        <span class="info">(2023)</span>
                    </span>
                </h3>
            </header>
        </article>
        <article class="box-film">
            <header class="article-header">
                <h3 class="film-title-norating">
                    <span class="film-title-user">2.</span>
                    <a href="/film/67890-another-movie/" 
                       title="Another Movie" 
                       class="film-title-name">
                       Another Movie
                    </a>
                    <span class="film-title-info">
                        <span class="info">(2022)</span>
                    </span>
                </h3>
            </header>
        </article>
    </div>
    """


@pytest.fixture
def sample_actor_html():
    """HTML sample containing actor data for parser testing."""
    return """
    <div class="creator-detail">
        <div class="film-creators">
            <h4>Hrají:</h4>
            <a href="/tvurce/123-john-doe/">John Doe</a>,
            <a href="/tvurce/456-jane-smith/">Jane Smith</a>,
            <span class="more-member-1 hidden">
                <a href="/tvurce/789-hidden-actor/">Hidden Actor</a>,
                <a href="/tvurce/101-another-hidden/">Another Hidden</a>
            </span>
        </div>
    </div>
    """


@pytest.fixture
def sample_actor_html_no_hidden():
    """Sample HTML containing actors without a hidden section."""
    return """
    <div class="creator-detail">
        <div class="film-creators">
            <h4>Hrají:</h4>
            <a href="/tvurce/123-john-doe/">John Doe</a>,
            <a href="/tvurce/456-jane-smith/">Jane Smith</a>
        </div>
    </div>
    """


class TestCommand:
    """Tests for the main Command class."""

    def test_add_arguments(self, command):
        """Test adding command-line arguments."""
        parser = Mock()
        command.add_arguments(parser)

        args, kwargs = parser.add_argument.call_args

        assert args[0] == "--limit"
        assert kwargs["default"] == 300
        assert kwargs["help"] == "Number of movies to load (default: 300)"

        assert callable(kwargs["type"])
        assert kwargs["type"].__name__ == "positive_int"

    @pytest.mark.parametrize("value", ["1", "300", "999"])
    def test_positive_int_validator_valid(self, command, value):
        parser = Mock()
        command.add_arguments(parser)
        positive_int = parser.add_argument.call_args[1]["type"]
        assert positive_int(value) == int(value)

    @pytest.mark.parametrize("value", ["0", "-1", "abc"])
    def test_positive_int_validator_invalid(self, command, value):
        parser = Mock()
        command.add_arguments(parser)
        positive_int = parser.add_argument.call_args[1]["type"]
        with pytest.raises(ValueError, match="Value must be a positive integer"):
            positive_int(value)

    def test_get_session(self, command):
        session = command.get_session()

        assert isinstance(session, requests.Session)
        assert "User-Agent" in session.headers
        assert "Accept-Language" in session.headers
        assert session.headers["Accept-Language"] == "cs,en;q=0.9"


class TestLoadTopCsfdMovies:
    """Tests for the method loading top movies."""

    @patch('movies.management.commands.load_top_movies.Command.get_session')
    def test_load_top_csfd_movies_success(self, mock_get_session, command, sample_movie_html):
        mock_session = Mock()
        mock_response = Mock()
        mock_response.content = sample_movie_html.encode('utf-8')
        mock_response.raise_for_status = Mock()
        mock_session.get.return_value = mock_response
        mock_get_session.return_value = mock_session

        result = command.load_top_csfd_movies(5)

        # Check that 5 movies were returned (duplicates are allowed)
        assert len(result) == 5

        # Check that specific movies are present in the result
        expected_movies = [
            {"title": "Test Movie", "url": "https://www.csfd.cz/film/12345-test-movie/"},
            {"title": "Another Movie", "url": "https://www.csfd.cz/film/67890-another-movie/"},
        ]

        for movie in expected_movies:
            assert movie in result


    @patch('movies.management.commands.load_top_movies.Command.get_session')
    def test_load_top_csfd_movies_network_error(self, mock_get_session, command):
        mock_session = Mock()
        mock_session.get.side_effect = requests.RequestException("Network error")
        mock_get_session.return_value = mock_session

        result = command.load_top_csfd_movies(5)

        assert result == []

    @patch('movies.management.commands.load_top_movies.Command.get_session')
    def test_load_top_csfd_movies_no_movies_found(self, mock_get_session, command):
        mock_session = Mock()
        mock_response = Mock()
        mock_response.content = b"<html><body>No movies here</body></html>"
        mock_response.raise_for_status = Mock()
        mock_session.get.return_value = mock_response
        mock_get_session.return_value = mock_session

        result = command.load_top_csfd_movies(5)

        assert result == []


class TestParseFilm:
    """Tests for the method parsing film actors."""

    @patch('movies.management.commands.load_top_movies.Command.get_session')
    def test_parse_film_with_hidden_actors(self, mock_get_session, command, sample_actor_html):
        mock_session = Mock()
        mock_response = Mock()
        mock_response.content = sample_actor_html.encode('utf-8')
        mock_response.raise_for_status = Mock()
        mock_response.encoding = 'utf-8'
        mock_session.get.return_value = mock_response
        mock_get_session.return_value = mock_session

        result = command.parse_film("https://www.csfd.cz/film/test/")

        assert len(result) == 4
        assert result[0]["name"] == "John Doe"
        assert result[0]["url"] == "https://www.csfd.cz/tvurce/123-john-doe/"
        assert result[1]["name"] == "Jane Smith"
        assert result[1]["url"] == "https://www.csfd.cz/tvurce/456-jane-smith/"
        assert result[2]["name"] == "Hidden Actor"
        assert result[3]["name"] == "Another Hidden"

    @patch('movies.management.commands.load_top_movies.Command.get_session')
    def test_parse_film_without_hidden_actors(self, mock_get_session, command, sample_actor_html_no_hidden):
        mock_session = Mock()
        mock_response = Mock()
        mock_response.content = sample_actor_html_no_hidden.encode('utf-8')
        mock_response.raise_for_status = Mock()
        mock_response.encoding = 'utf-8'
        mock_session.get.return_value = mock_response
        mock_get_session.return_value = mock_session

        result = command.parse_film("https://www.csfd.cz/film/test/")

        assert len(result) == 2
        assert result[0]["name"] == "John Doe"
        assert result[1]["name"] == "Jane Smith"

    @patch('movies.management.commands.load_top_movies.Command.get_session')
    def test_parse_film_no_cast_section(self, mock_get_session, command):
        mock_session = Mock()
        mock_response = Mock()
        mock_response.content = b"<html><body>No cast section</body></html>"
        mock_response.raise_for_status = Mock()
        mock_response.encoding = 'utf-8'
        mock_session.get.return_value = mock_response
        mock_get_session.return_value = mock_session

        result = command.parse_film("https://www.csfd.cz/film/test/")

        assert result == []

    @patch('movies.management.commands.load_top_movies.Command.get_session')
    def test_parse_film_network_error(self, mock_get_session, command):
        mock_session = Mock()
        mock_session.get.side_effect = requests.RequestException("Network error")
        mock_get_session.return_value = mock_session

        with pytest.raises(requests.RequestException):
            command.parse_film("https://www.csfd.cz/film/test/")


@pytest.mark.django_db
class TestSaveMovieWithActors:
    """Tests for the method saving a movie with actors to the database."""

    def test_save_new_movie_with_actors(self, command):
        film_data = {
            "title": "Test Movie",
            "url": "https://www.csfd.cz/film/test-movie/"
        }
        actors_data = [
            {"name": "John Doe", "url": "https://www.csfd.cz/tvurce/john-doe/"},
            {"name": "Jane Smith", "url": "https://www.csfd.cz/tvurce/jane-smith/"}
        ]

        command.stdout = Mock()

        command.save_movie_with_actors(film_data, actors_data)

        assert Film.objects.count() == 1
        film = Film.objects.first()
        assert film.title == "Test Movie"
        assert film.url == "https://www.csfd.cz/film/test-movie/"

        assert Actor.objects.count() == 2
        actor_names = list(Actor.objects.values_list("name", flat=True))
        assert "John Doe" in actor_names
        assert "Jane Smith" in actor_names

        assert FilmActor.objects.count() == 2
        assert film.actors.count() == 2

    def test_save_duplicate_movie_actor_link(self, command):
        film = Film.objects.create(
            title="Test Movie",
            url="https://www.csfd.cz/film/test-movie/"
        )
        actor = Actor.objects.create(
            name="John Doe",
            url="https://www.csfd.cz/tvurce/john-doe/"
        )
        FilmActor.objects.create(film=film, actor=actor)

        film_data = {
            "title": "Test Movie",
            "url": "https://www.csfd.cz/film/test-movie/"
        }
        actors_data = [
            {"name": "John Doe", "url": "https://www.csfd.cz/tvurce/john-doe/"}
        ]

        command.stdout = Mock()

        command.save_movie_with_actors(film_data, actors_data)

        assert FilmActor.objects.count() == 1

    @patch('movies.management.commands.load_top_movies.Actor.objects.get_or_create')
    def test_save_movie_with_actors_exception_rollback(self, mock_get_or_create, command):
        film_data = {"title": "Fail Film", "url": "https://www.csfd.cz/film/fail/"}
        actors_data = [{"name": "Actor X", "url": "https://www.csfd.cz/tvurce/actor-x/"}]

        mock_get_or_create.side_effect = Exception("DB failure")

        command.stdout = Mock()

        with pytest.raises(Exception, match="DB failure"):
            command.save_movie_with_actors(film_data, actors_data)

        # Ensure nothing saved due to rollback
        assert Film.objects.count() == 0
        assert Actor.objects.count() == 0


@pytest.mark.django_db
class TestHandleCommand:
    """Tests for the handle() method of the Command."""

    @patch('movies.management.commands.load_top_movies.Command.load_top_csfd_movies')
    @patch('movies.management.commands.load_top_movies.Command.parse_film')
    @patch('movies.management.commands.load_top_movies.Command.save_movie_with_actors')
    def test_handle_loads_and_saves_movies(self, mock_save, mock_parse, mock_load, command):
        mock_load.return_value = [
            {"title": "Movie 1", "url": "https://www.csfd.cz/film/1/"},
            {"title": "Movie 2", "url": "https://www.csfd.cz/film/2/"}
        ]

        mock_parse.side_effect = [
            [{"name": "Actor A", "url": "https://www.csfd.cz/tvurce/a/"}],
            [{"name": "Actor B", "url": "https://www.csfd.cz/tvurce/b/"}]
        ]

        command.handle(limit=2)

        assert mock_load.called
        assert mock_parse.call_count == 2
        assert mock_save.call_count == 2
