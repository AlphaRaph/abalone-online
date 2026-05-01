import json
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from .models import Game
from .engine import AbaloneEngine

class GameConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.game_code = self.scope['url_route']['kwargs']['game_code']
        self.room_group_name = f'game_{self.game_code}'

        # Verify game exists
        self.game = await self.get_game(self.game_code)
        if not self.game:
            await self.close()
            return

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

        # Send current board state on connect
        black_count = sum(1 for v in self.game.board_state.values() if v == 'black')
        white_count = sum(1 for v in self.game.board_state.values() if v == 'white')
        await self.send(text_data=json.dumps({
            'type': 'state_update',
            'state': self.game.board_state,
            'turn': self.game.turn,
            'status': self.game.status,
            'history_length': len(self.game.history) if self.game.history else 0,
            'score_black': 14 - white_count,
            'score_white': 14 - black_count,
            'info': ''
        }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        data = json.dumps({})
        try:
            data = json.loads(text_data)
        except:
            return

        message_type = data.get('type')
        if message_type == 'move':
            await self.handle_move(data)
        elif message_type == 'undo':
            await self.handle_undo(data)
        elif message_type == 'rematch':
            await self.handle_rematch(data)

    async def handle_move(self, data):
        marbles = data.get('marbles', [])
        direction = str(data.get('direction', ''))
        player_color = data.get('player', '')

        self.game = await self.get_game(self.game_code)
        
        # Validation du tour
        if self.game.status != 'playing':
            await self.send_error("Partie non en cours.")
            return
        if self.game.turn != player_color:
            await self.send_error("Ce n'est pas votre tour.")
            return
        if direction not in AbaloneEngine.DIRECTIONS:
            await self.send_error("Direction invalide.")
            return

        # Appliquer le mouvement
        success, msg, new_state = AbaloneEngine.apply_move(self.game.board_state, marbles, direction, player_color)
        
        if success:
            # Sauvegarder l'état précédent dans l'historique
            if type(self.game.history) is not list:
                self.game.history = []
            self.game.history.append(self.game.board_state)

            # Update state
            self.game.board_state = new_state
            self.game.turn = 'white' if self.game.turn == 'black' else 'black'
            
            # TODO: Vérifier victoire (count black/white marbles in new_state)
            black_count = sum(1 for v in new_state.values() if v == 'black')
            white_count = sum(1 for v in new_state.values() if v == 'white')
            
            if black_count <= 8: # 14 - 6 = 8
                self.game.status = 'finished'
                msg = "White wins!"
            elif white_count <= 8:
                self.game.status = 'finished'
                msg = "Black wins!"

            await self.save_game(self.game)

            await self.broadcast_state(msg)
        else:
            await self.send_error(msg)
        
    async def handle_undo(self, data):
        self.game = await self.get_game(self.game_code)
        
        if not self.game.history or len(self.game.history) == 0:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Rien à annuler.'
            }))
            return
            
        player_color = data.get('player')
        
        # Seul le joueur qui vient de jouer (ou le gagnant) peut annuler
        if self.game.status == 'playing' and self.game.turn == player_color:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Ce n\'est pas à vous d\'annuler ce coup.'
            }))
            return
            
        # Récupérer le dernier état
        previous_state = self.game.history.pop()
        
        self.game.board_state = previous_state
        self.game.turn = 'white' if self.game.turn == 'black' else 'black'
        
        # Si la partie était finie, on la relance
        if self.game.status == 'finished':
            self.game.status = 'playing'
            
        await self.save_game(self.game)
        
        await self.broadcast_state('Coup annulé.')

    async def handle_rematch(self, data):
        self.game = await self.get_game(self.game_code)
        player_color = data.get('player')
        
        if player_color == 'black':
            self.game.rematch_requested_black = True
        elif player_color == 'white':
            self.game.rematch_requested_white = True
            
        if self.game.rematch_requested_black and self.game.rematch_requested_white:
            # Les deux veulent rejouer
            self.game.board_state = AbaloneEngine.get_initial_state()
            self.game.history = []
            self.game.turn = 'black'
            self.game.status = 'playing'
            self.game.rematch_requested_black = False
            self.game.rematch_requested_white = False
            await self.save_game(self.game)
            await self.broadcast_state('Nouvelle partie démarrée !')
        else:
            await self.save_game(self.game)
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'game_message',
                    'message_type': 'rematch_requested',
                    'player': player_color
                }
            )

    async def broadcast_state(self, info=""):
        black_count = sum(1 for v in self.game.board_state.values() if v == 'black')
        white_count = sum(1 for v in self.game.board_state.values() if v == 'white')
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'game_message',
                'message_type': 'state_update',
                'state': self.game.board_state,
                'turn': self.game.turn,
                'status': self.game.status,
                'info': info,
                'history_length': len(self.game.history) if self.game.history else 0,
                'score_black': 14 - white_count,
                'score_white': 14 - black_count
            }
        )

    async def send_error(self, msg):
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': msg
        }))

    async def game_message(self, event):
        payload = event.copy()
        if 'message_type' in payload:
            payload['type'] = payload['message_type']
        await self.send(text_data=json.dumps(payload))

    @sync_to_async
    def get_game(self, code):
        try:
            return Game.objects.get(code=code)
        except Game.DoesNotExist:
            return None

    @sync_to_async
    def save_game(self, game):
        game.save()
