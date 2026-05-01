from django.db import models
from django.utils.crypto import get_random_string
from .engine import AbaloneEngine

def generate_game_code():
    return get_random_string(length=6, allowed_chars='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')

class Game(models.Model):
    STATUS_CHOICES = (
        ('waiting', 'En attente'),
        ('playing', 'En cours'),
        ('finished', 'Terminé'),
    )

    code = models.CharField(max_length=6, default=generate_game_code, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='waiting')
    
    player_black_name = models.CharField(max_length=50, blank=True, null=True)
    player_black_session = models.CharField(max_length=40, blank=True, null=True)
    
    player_white_name = models.CharField(max_length=50, blank=True, null=True)
    player_white_session = models.CharField(max_length=40, blank=True, null=True)
    
    turn = models.CharField(max_length=10, default='black') # 'black' ou 'white'
    board_state = models.JSONField(default=AbaloneEngine.get_initial_state) # Stockera la position des billes
    history = models.JSONField(default=list, blank=True)
    
    rematch_requested_black = models.BooleanField(default=False)
    rematch_requested_white = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Game {self.code} ({self.status})"

    def is_full(self):
        return self.player_black_session and self.player_white_session
