from django.contrib import admin
from .models import Film, Actor, FilmActor

@admin.register(Film)
class FilmAdmin(admin.ModelAdmin):
    list_display = ('title', 'url', 'title_normalized')
    search_fields = ('title', 'title_normalized')
    readonly_fields = ('title_normalized',)
    list_per_page = 50

@admin.register(Actor)
class ActorAdmin(admin.ModelAdmin):
    list_display = ('name', 'url', 'name_normalized')
    search_fields = ('name', 'name_normalized')
    readonly_fields = ('name_normalized',)
    list_per_page = 50

@admin.register(FilmActor)
class MovieActorAdmin(admin.ModelAdmin):
    list_display = ('film', 'actor')    
    list_filter = ('film', 'actor')
    search_fields = ('film__title', 'actor__name')    
    list_per_page = 100

    autocomplete_fields = ('film', 'actor')
