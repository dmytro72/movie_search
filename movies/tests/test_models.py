import pytest
from movies.models import Actor, Film, FilmActor

@pytest.mark.django_db
def test_actor_creation_and_normalization():
    actor = Actor.objects.create(name="Řehoř", url="https://example.com/rehor")
    assert actor.name_normalized == "rehor"
    assert str(actor) == "Řehoř"


@pytest.mark.django_db
def test_film_creation_and_normalization():
    film = Film.objects.create(title="Pelíšky", url="https://example.com/pelisky")
    assert film.title_normalized == "pelisky"
    assert str(film) == "Pelíšky"


@pytest.mark.django_db
def test_movie_actor_relationship():
    actor = Actor.objects.create(name="Řehoř", url="https://example.com/rehor")
    film = Film.objects.create(title="Pelíšky", url="https://example.com/pelisky")
    movie_actor = FilmActor.objects.create(actor=actor, film=film)
    assert movie_actor.actor == actor
    assert movie_actor.film == film


@pytest.mark.django_db
def test_actor_str_representation():
    actor = Actor.objects.create(name="Řehoř", url="https://example.com/rehor")
    assert str(actor) == "Řehoř"


@pytest.mark.django_db
def test_film_str_representation():
    film = Film.objects.create(title="Pelíšky", url="https://example.com/pelisky")
    assert str(film) == "Pelíšky"


@pytest.mark.django_db
def test_movie_actor_str_representation():
    actor = Actor.objects.create(name="Řehoř", url="https://example.com/rehor")
    film = Film.objects.create(title="Pelíšky", url="https://example.com/pelisky")
    movie_actor = FilmActor.objects.create(actor=actor, film=film)
    assert str(movie_actor) == "Řehoř - Pelíšky"
