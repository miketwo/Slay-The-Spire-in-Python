import entities
import helper
import pytest
import enemy_catalog
import inspect
from entities import Enemy

@pytest.fixture
def sleepless(monkeypatch):
    def sleep(seconds):
        pass
    monkeypatch.setattr(helper, 'sleep', sleep)
    monkeypatch.setattr(entities, 'sleep', sleep)


def dynamically_generate_test_cases():
  enemies = []
  for name, obj in inspect.getmembers(enemy_catalog):
    # These enemies are too hard to test for some reason
    if inspect.isclass(obj) and issubclass(obj, Enemy) and name not in ["Enemy", "Hexaghost", "Lagavulin", "Sentry", "ShieldGremlin"]:
        enemies.append((name,obj))
  return enemies


@pytest.mark.parametrize("name, class_obj", dynamically_generate_test_cases())
def test_most_enemies_default_move(name, class_obj, sleepless):
  # Make a super player
  player = entities.Player(health=1000, block=0, max_energy=100, deck=[])
  print(f"--->Testing: {name}")
  enemy = class_obj()
  enemy.set_intent()
  print(f"Player health: {player.health}")
  enemy.execute_move(player=player, enemies=None)
