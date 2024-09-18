from entities import Player
import pytest
import helper
import entities
import game
import shop
import random
from definitions import CombatTier
import enemy_catalog
import items
from ansimarkup import ansiprint

def replacement_clear_screen():
    '''Replacement for view.clear() so that I can see the test output'''
    print("\n--------------------------\n")

def patched_input(*args, **kwargs):
    return str(random.randint(1,9))

@pytest.mark.skip("Not yet working")
def test_gamblers_brew_apply(monkeypatch):
    # "Discard any number of cards, then draw that many."
    player = Player.create_player()
    player.draw_pile = random.sample(player.deck, len(player.deck))
    player.draw_cards(5)
    assert len(player.potions) == 0
    assert len(player.hand) == 5
    assert len(player.discard_pile) == 0
    inputs = iter(["1", "3", "4", "exit"])
    with monkeypatch.context() as m:
        # m.setattr("builtins.input", lambda *args, **kwargs: next(inputs))
        m.setattr("game.view.clear", replacement_clear_screen)
        potion = items.GamblersBrew()
        potion.apply(player)
        assert len(player.potions) == 0
        assert len(player.hand) == 5
        assert len(player.discard_pile) == 3