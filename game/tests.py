from django.test import TestCase
from game.engine import AbaloneEngine

class AbaloneEngineTests(TestCase):
    def setUp(self):
        self.initial_state = AbaloneEngine.get_initial_state()

    def test_initial_state(self):
        # 14 black, 14 white
        black_count = sum(1 for v in self.initial_state.values() if v == 'black')
        white_count = sum(1 for v in self.initial_state.values() if v == 'white')
        
        self.assertEqual(black_count, 14)
        self.assertEqual(white_count, 14)
        
        # Check specific initial positions
        self.assertEqual(self.initial_state.get('0,4'), 'black')
        self.assertEqual(self.initial_state.get('0,-4'), 'white')

    def test_valid_inline_move(self):
        state = self.initial_state.copy()
        
        # Moving (0,2) to +r (0,3) is blocked by own marble!
        # Let's try moving (0,2) to -r (0,1). Direction '2' is (0, -1).
        success, msg, new_state = AbaloneEngine.apply_move(state, ["0,2"], '2', 'black')
        print("DEBUG:", msg, state.get("0,1"))
        self.assertTrue(success, msg)
        self.assertNotIn("0,2", new_state)
        self.assertEqual(new_state.get("0,1"), 'black')

    def test_invalid_move_blocked_by_own(self):
        state = self.initial_state.copy()
        
        # Move (0,2) to +r (0,3). Direction '5' is (0, 1). (0,3) is black.
        success, msg, new_state = AbaloneEngine.apply_move(state, ["0,2"], '5', 'black')
        self.assertFalse(success)
        self.assertIn("vos billes", msg)

    def test_valid_sumito_2v1(self):
        state = {
            "0,1": "black",
            "0,0": "black",
            "0,-1": "white"
        }
        # Black pushes white in direction '2' (0, -1)
        # Line is 0,1 -> 0,0 -> 0,-1
        success, msg, new_state = AbaloneEngine.apply_move(state, ["0,1", "0,0"], '2', 'black')
        self.assertTrue(success, msg)
        
        # Expected: black at 0,0 and 0,-1. White pushed to 0,-2.
        self.assertNotIn("0,1", new_state)
        self.assertEqual(new_state.get("0,0"), "black")
        self.assertEqual(new_state.get("0,-1"), "black")
        self.assertEqual(new_state.get("0,-2"), "white")

    def test_invalid_sumito_equal_power(self):
        state = {
            "0,0": "black",
            "0,-1": "white"
        }
        # 1v1 push should fail
        success, msg, new_state = AbaloneEngine.apply_move(state, ["0,0"], '2', 'black')
        self.assertFalse(success)
        self.assertIn("puissance", msg)

    def test_sumito_eject(self):
        state = {
            "0,-3": "black",
            "0,-4": "black",
            "0,-5": "white" # wait, valid coords? 0,-5 is invalid.
        }
        # Actually 0,-4 is edge.
        state2 = {
            "0,-3": "black",
            "0,-2": "black",
            "0,-4": "white"
        }
        # Black pushes white off the board! Direction '2' (0, -1).
        success, msg, new_state = AbaloneEngine.apply_move(state2, ["0,-2", "0,-3"], '2', 'black')
        self.assertTrue(success, msg)
        
        # White should be ejected (removed from board)
        self.assertEqual(new_state.get("0,-4"), "black")
        self.assertEqual(new_state.get("0,-3"), "black")
        
        # Count white marbles
        self.assertEqual(sum(1 for v in new_state.values() if v == 'white'), 0)
        
    def test_valid_broadside(self):
        state = {
            "0,0": "black",
            "1,0": "black"
        }
        # Move laterally in direction '5' (0, 1) -> +r
        success, msg, new_state = AbaloneEngine.apply_move(state, ["0,0", "1,0"], '5', 'black')
        self.assertTrue(success, msg)
        
        self.assertNotIn("0,0", new_state)
        self.assertNotIn("1,0", new_state)
        self.assertEqual(new_state.get("0,1"), "black")
        self.assertEqual(new_state.get("1,1"), "black")
