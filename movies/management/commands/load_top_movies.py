import re
import time
import random
import requests
from typing import List, Dict
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand
from django.db import transaction
from movies.utils import normalize
from movies.models import Actor, Film, FilmActor


class Command(BaseCommand):
    help = "Loads the Top 300 movies from csfd.cz along with their actors."

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

    def add_arguments(self, parser):
        """
        Adds command-line arguments to the parser.
        """

        def positive_int(value):
            """
            Validates that the value is a positive integer.
            """
            try:
                ivalue = int(value)
                if ivalue <= 0:
                    raise ValueError
            except ValueError:
                raise ValueError("Value must be a positive integer")
            return ivalue            
           
        parser.add_argument(
            "--limit",
            type=positive_int,
            default=self.DEFAULT_MOVIE_LIMIT,
            help=f"Number of movies to load (default: {self.DEFAULT_MOVIE_LIMIT})",
        )

    def handle(self, *args, **options) -> None:
        """
        The main entry point for the command.
        """
        limit = options["limit"]

        try:            
            films = self.load_top_csfd_movies(limit)
            self.stdout.write(self.style.SUCCESS(f"Loaded {len(films)} movies from CSFD"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error fetching top movies: {e}"))
            return

        # process each movie
        for i, film_data in enumerate(films, 1):
            self.stdout.write(f"Processing movie {i}/{len(films)}: {film_data['title']}")

            try:
                actors_data = self.parse_film(film_data["url"])
                self.stdout.write(f"Found {len(actors_data)} actors")
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Error fetching actors for {film_data['title']}: {e}")
                )
                actors_data = []
            
            try:
                self.save_movie_with_actors(film_data, actors_data)
                self.stdout.write(self.style.SUCCESS(f"Saved: {film_data['title']}"))
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Error saving movie {film_data['title']}: {e}")
                )
            
            # pause between requests
            time.sleep(random.uniform(self.MIN_REQUEST_DELAY, self.MAX_REQUEST_DELAY))
    
    def get_session(self) -> requests.Session:
        """
        Creates and returns a requests session with custom headers.

        Returns:
            requests.Session: Configured HTTP session.
        """
        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": self.USER_AGENT,
                "Accept-Language": self.ACCEPT_LANGUAGE
            }
        )
        return session

    def load_top_csfd_movies(self, limit: int) -> List[Dict[str,str]]:
        """
        Fetches a list of top movies from CSFD.cz.

        HTML structure for each movie:
        <header class="article-header">
            <h3 class="film-title-norating">
                <span class="film-title-user">300.</span>               # Movie ranking number with a trailing dot
                <a href="/film/141680-harakiri/"                        # Link to the movie page
                   title="Harakiri"
                   class="film-title-name">
                   Harakiri                                             # Movie title
                </a>
                <span class="film-title-info">
                    <span class="info">(1962)</span>                   # Year of release (optional)
                </span>
            </h3>
        </header>

        Pagination structure:
        <div class="box-more-bar box-more-bar-charts">
            <a href="/zebricky/filmy/nejlepsi/">1</a>
            <a href="/zebricky/filmy/nejlepsi/?from=100">100</a>
            <a href="/zebricky/filmy/nejlepsi/?from=200">200</a>
            <span class="current">300</span>
            <a href="/zebricky/filmy/nejlepsi/?from=400">400</a>
            <a href="/zebricky/filmy/nejlepsi/?from=500">500</a>
            ...
        </div>

        Args:
            limit (int): The maximum number of movies to fetch.

        Returns:
            List[Dict[str, str]]: A list of movie dictionaries with title and URL.
        """
        session = self.get_session()
        films = []
        processed = 0
        from_param = 0
        
        while processed < limit:
            # Construct the URL with the 'from' parameter for pagination
            if from_param > 0:
                url = f"{self.CSFD_TOP_MOVIES_URL}?from={from_param}"
            else:
                url = self.CSFD_TOP_MOVIES_URL
                
            self.stdout.write(f"Fetching movies from: {url}")
            
            try:
                response = session.get(url)
                response.raise_for_status()
            except requests.RequestException as e:
                self.stdout.write(self.style.ERROR(f"Error fetching {url}: {e}"))
                break

            soup = BeautifulSoup(response.content, "html.parser")
            
            # Find movies based on the HTML structure
            movie_elements = soup.select(self.MOVIE_SELECTOR)
            
            if not movie_elements:
                self.stdout.write(self.style.WARNING(f"No movies found on page: {url}"))
                break
            
            for element in movie_elements:
                if processed >= limit:
                    break
                    
                title = element.get_text(strip=True)
                href = element.get("href")
                
                if title and href:
                    url = self.CSFD_BASE_URL + href
                    films.append({"title": title, "url": url})
                    processed += 1
            
            # Move to the next page
            from_param += self.MOVIES_PER_CSFD_PAGE
                
        return films[:limit]
    
    def parse_film(self, film_link: str) -> List[Dict[str, str]]:
        """
        Fetches actor data from a given movie URL.

        HTML structure to parse:
        <div>
            <h4>Hrají:</h4>
            <a href="/tvurce/29533-takuja-kimura/">Takuja Kimura</a>, 
            <a href="/tvurce/263523-cieko-baiso/">Čieko Baišó</a>,
            ...
            <!-- This part is optional - it may or may not be present -->
            <span class="more-member-1 hidden">
                <a href="/tvurce/348385-seidzi-sasaki/">Seidži Sasaki</a>,
                ...
            </span>
        </div>
        
        Args:
            film_link (str): The URL of the movie.
            
        Returns:
            List[Dict[str, str]]: A list of actor dictionaries with name and URL.
        """        
        session = self.get_session()
        response = session.get(film_link)
        response.raise_for_status()
        response.encoding = 'utf-8'

        soup = BeautifulSoup(response.content, "html.parser")
        actors = []

        # Find the section with the header "Hrají:" (meaning "Starring:")
        cast_section = soup.find('h4', string=re.compile(self.CAST_HEADER_PATTERN, re.IGNORECASE))

        if not cast_section:
            return actors

        # Get the parent div of the header
        cast_div = cast_section.parent

        if not cast_div:
            return actors

        # Find all actor links within this div
        # Includes both visible and hidden actors (e.g., in spans with class "more-member-1 hidden")
        actor_links = cast_div.find_all('a', href=re.compile(self.ACTOR_URL_PATTERN))

        for link in actor_links:
            # Extract actor URL and name
            actor_url = link.get('href', '').strip()
            actor_name = link.get_text(strip=True)

            # Ensure data is not empty
            if actor_url and actor_name:
                # Construct full URL if relative
                if actor_url.startswith('/'):
                    actor_url = self.CSFD_BASE_URL + actor_url

                actors.append({
                    'name': actor_name,
                    'url': actor_url
                })

        return actors
    
    @transaction.atomic
    def save_movie_with_actors(
        self,
        film_data: Dict[str, str],
        actors_data: List[Dict[str, str]],
    ) -> None:
        """
        Saves a movie and its actors to the database.

        Args:
            film_data (Dict[str, str]): Film information including title and URL.
            actors_data (List[Dict[str, str]]): A list of actors associated with the film.
        """       
        # Create or get the film
        film, created = Film.objects.get_or_create(
            url=film_data["url"],
            defaults={"title": film_data["title"]}
        )

        if created:
            self.stdout.write(f"Created new film: {film.title}")

        # Process actors
        for actor_data in actors_data:
            # Create or get the actor
            actor, created = Actor.objects.get_or_create(
                url=actor_data["url"],
                defaults={"name": actor_data["name"]}
            )
            
            if created:
                self.stdout.write(f"  Created new actor: {actor.name}")
            
            # Create the link between film and actor
            _, created = FilmActor.objects.get_or_create(
                film=film,
                actor=actor
            )
            
            if created:
                self.stdout.write(f"  Linked actor {actor.name} to film {film.title}")