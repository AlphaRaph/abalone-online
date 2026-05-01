class AbaloneEngine:
    DIRECTIONS = {
        '0': (1, 0),    # +q
        '1': (1, -1),   # +q, -r
        '2': (0, -1),   # -r
        '3': (-1, 0),   # -q
        '4': (-1, 1),   # -q, +r
        '5': (0, 1),    # +r
    }

    @staticmethod
    def get_initial_state():
        state = {}
        # Black marbles (top)
        for q in range(-4, 1): state[f"{q},4"] = 'black'
        for q in range(-4, 2): state[f"{q},3"] = 'black'
        for q in range(-2, 1): state[f"{q},2"] = 'black'

        # White marbles (bottom)
        for q in range(0, 5): state[f"{q},-4"] = 'white'
        for q in range(-1, 5): state[f"{q},-3"] = 'white'
        for q in range(0, 3): state[f"{q},-2"] = 'white'

        return state

    @staticmethod
    def is_valid_coord(q, r):
        s = -q - r
        return max(abs(q), abs(r), abs(s)) <= 4

    @staticmethod
    def get_line(state, q, r, dq, dr, player, max_marbles=3):
        # Cherche la ligne de billes du joueur en commençant par q, r dans la direction dq, dr (sens inverse de la poussée)
        line = []
        curr_q, curr_r = q, r
        while len(line) < max_marbles:
            coord = f"{curr_q},{curr_r}"
            if state.get(coord) == player:
                line.append((curr_q, curr_r))
                curr_q -= dq
                curr_r -= dr
            else:
                break
        return line

    @staticmethod
    def apply_move(state, marbles, direction, player):
        """
        marbles: list of "q,r" strings (ex: ["0,2", "0,3", "0,4"])
        direction: string key from DIRECTIONS ('0' to '5')
        player: 'black' or 'white'
        """
        dq, dr = AbaloneEngine.DIRECTIONS[direction]
        new_state = state.copy()
        
        # 1. Validation de base
        if len(marbles) < 1 or len(marbles) > 3:
            return False, "Nombre de billes invalide.", new_state

        parsed_marbles = []
        for m in marbles:
            q, r = map(int, m.split(','))
            if state.get(m) != player:
                return False, "Ce ne sont pas vos billes.", new_state
            parsed_marbles.append((q, r))

        # 2. S'assurer que les billes forment une ligne contiguë si len > 1
        if len(parsed_marbles) > 1:
            # Pour vérifier la contiguïté, on pourrait calculer le vecteur entre les billes.
            # Plus simple: s'attendre à ce que les billes soient alignées.
            # On trie pour faciliter.
            pass # TODO: validation de l'alignement pour les mouvements latéraux (Broadside)

        # 3. Déterminer si c'est un mouvement en ligne (In-Line) ou latéral (Broadside)
        # In-line si la direction correspond à l'alignement des billes.
        is_inline = False
        if len(parsed_marbles) > 1:
            q1, r1 = parsed_marbles[0]
            q2, r2 = parsed_marbles[1]
            diff_q, diff_r = q2 - q1, r2 - r1
            # Normaliser
            m_len = max(abs(diff_q), abs(diff_r), abs(-diff_q-diff_r))
            norm_q, norm_r = diff_q // m_len, diff_r // m_len
            if (norm_q, norm_r) == (dq, dr) or (-norm_q, -norm_r) == (dq, dr):
                is_inline = True

        # 4. Exécuter le mouvement
        if not is_inline and len(parsed_marbles) > 1:
            # Broadside: toutes les cases cibles doivent être vides
            for q, r in parsed_marbles:
                tq, tr = q + dq, r + dr
                if not AbaloneEngine.is_valid_coord(tq, tr) or state.get(f"{tq},{tr}") is not None:
                    return False, "Déplacement latéral impossible.", new_state
            
            # Appliquer
            for q, r in parsed_marbles:
                del new_state[f"{q},{r}"]
            for q, r in parsed_marbles:
                new_state[f"{q+dq},{r+dr}"] = player
            return True, "Déplacement réussi.", new_state

        else:
            # In-line ou 1 bille: Gérer le Sumito (poussée)
            # Trouver la bille la plus "en avant"
            # On trie les billes selon la direction
            parsed_marbles.sort(key=lambda coord: coord[0]*dq + coord[1]*dr, reverse=True)
            front_q, front_r = parsed_marbles[0]
            
            opponent = 'white' if player == 'black' else 'black'
            
            # Regarder devant la ligne
            push_q, push_r = front_q + dq, front_r + dr
            opponent_count = 0
            opponent_marbles = []
            
            while True:
                coord = f"{push_q},{push_r}"
                if not AbaloneEngine.is_valid_coord(push_q, push_r):
                    # Bord du plateau
                    break
                if state.get(coord) == opponent:
                    opponent_count += 1
                    opponent_marbles.append((push_q, push_r))
                    push_q += dq
                    push_r += dr
                else:
                    break
            
            if opponent_count >= len(parsed_marbles):
                return False, "Pas assez de puissance pour pousser.", new_state
            
            # Vérifier la case juste après les adversaires (si sur le plateau)
            after_coord = f"{push_q},{push_r}"
            if AbaloneEngine.is_valid_coord(push_q, push_r) and state.get(after_coord) == player:
                 return False, "Mouvement bloqué par l'une de vos billes.", new_state
                 
            if AbaloneEngine.is_valid_coord(push_q, push_r) and state.get(after_coord) == opponent:
                 return False, "Mouvement bloqué par une bille adverse.", new_state

            # Appliquer
            # On efface les nôtres
            for q, r in parsed_marbles:
                del new_state[f"{q},{r}"]
            # On efface les adversaires
            for q, r in opponent_marbles:
                del new_state[f"{q},{r}"]
                
            # On replace les nôtres avancées de 1
            for q, r in parsed_marbles:
                new_state[f"{q+dq},{r+dr}"] = player
            # On replace les adversaires avancées de 1 (si encore sur le plateau)
            for q, r in opponent_marbles:
                tq, tr = q+dq, r+dr
                if AbaloneEngine.is_valid_coord(tq, tr):
                    new_state[f"{tq},{tr}"] = opponent
                    
            return True, "Déplacement réussi.", new_state
