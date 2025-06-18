import logging
from django.db import models
from movies.utils import normalize


logger = logging.getLogger('movies.models')

class Actor(models.Model):
    name = models.CharField(max_length=255)
    url = models.URLField(unique=True)
    name_normalized = models.CharField(max_length=255, editable=False, db_index=True)

    def save(self, *args, **kwargs):
        self.name_normalized = normalize(self.name)
        logger.info(f"Saving actor: {self.name}")
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
    

class Film(models.Model):
    title = models.CharField(max_length=255)
    url = models.URLField(unique=True)
    title_normalized = models.CharField(max_length=255, editable=False, db_index=True)
    actors = models.ManyToManyField("Actor", through="FilmActor", related_name="films")

    def save(self, *args, **kwargs):
        self.title_normalized = normalize(self.title)
        logger.info(f"Saving film: {self.title}")
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title
    

class FilmActor(models.Model):
    actor = models.ForeignKey(Actor, on_delete=models.CASCADE)
    film = models.ForeignKey(Film, on_delete=models.CASCADE)

    class Meta:
        unique_together = (("actor", "film"),)

    def __str__(self):
        return f"{self.actor.name} - {self.film.title}"