from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.db import models
from .models import Game

def get_or_create_session(request):
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key

def home(request):
    session_key = get_or_create_session(request)
    
    # Check if user is already in a game
    active_game = Game.objects.filter(status__in=['waiting', 'playing']).filter(
        models.Q(player_black_session=session_key) | models.Q(player_white_session=session_key)
    ).first()

    context = {'active_game': active_game}
    return render(request, 'game/home.html', context)

def create_game(request):
    if request.method == 'POST':
        game = Game.objects.create()
        return redirect('lobby', game_code=game.code)
    return redirect('home')

def join_game(request):
    if request.method == 'POST':
        code = request.POST.get('code', '').strip().upper()
        if Game.objects.filter(code=code).exists():
            game = Game.objects.get(code=code)
            if game.status == 'waiting':
                return redirect('lobby', game_code=game.code)
            elif game.status == 'playing':
                # Can only join if they are already a player
                session_key = get_or_create_session(request)
                if session_key in [game.player_black_session, game.player_white_session]:
                    return redirect('play', game_code=game.code)
                else:
                    messages.error(request, "Cette partie est déjà complète.")
            else:
                messages.error(request, "Cette partie est terminée.")
        else:
            messages.error(request, "Code invalide.")
    return redirect('home')

def lobby(request, game_code):
    game = get_object_or_404(Game, code=game_code)
    session_key = get_or_create_session(request)

    # Si la partie a démarré et le joueur en fait partie, go play
    if game.status == 'playing':
        if session_key in [game.player_black_session, game.player_white_session]:
            return redirect('play', game_code=game.code)

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        if username:
            if not game.player_black_session:
                game.player_black_session = session_key
                game.player_black_name = username
                game.save()
            elif not game.player_white_session and game.player_black_session != session_key:
                game.player_white_session = session_key
                game.player_white_name = username
                game.status = 'playing' # Les deux joueurs sont là
                game.save()
            
            # Si les deux sont là, redirect to play
            if game.is_full():
                return redirect('play', game_code=game.code)

    # Le joueur est-il déjà enregistré dans la partie ?
    is_registered = session_key in [game.player_black_session, game.player_white_session]

    context = {
        'game': game,
        'is_registered': is_registered,
        'session_key': session_key,
    }
    return render(request, 'game/lobby.html', context)

def play(request, game_code):
    game = get_object_or_404(Game, code=game_code)
    session_key = get_or_create_session(request)

    if session_key == game.player_black_session:
        player_color = 'black'
    elif session_key == game.player_white_session:
        player_color = 'white'
    else:
        messages.error(request, "Vous n'êtes pas joueur dans cette partie.")
        return redirect('home')

    context = {
        'game': game,
        'player_color': player_color,
        'black_name': game.player_black_name or 'Joueur Noir',
        'white_name': game.player_white_name or 'Joueur Blanc',
    }
    return render(request, 'game/play.html', context)

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

def leave_game(request, game_code):
    game = get_object_or_404(Game, code=game_code)
    session_key = get_or_create_session(request)

    left = False
    if session_key == game.player_black_session:
        game.player_black_session = None
        game.player_black_name = None
        game.status = 'waiting'
        game.save()
        left = True
    elif session_key == game.player_white_session:
        game.player_white_session = None
        game.player_white_name = None
        game.status = 'waiting'
        game.save()
        left = True
        
    if left:
        messages.success(request, "Vous avez quitté la partie.")
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"game_{game.code}",
            {
                'type': 'game_message',
                'message_type': 'opponent_left'
            }
        )
    
    return redirect('home')
