import entities
import helper
import pytest
import enemy_catalog
import random

@pytest.fixture
def ei():
  ei = helper.EffectInterface()
  return ei

@pytest.fixture
def player():
  player = entities.create_player()
  return player

@pytest.fixture
def enemy():
  enemy = enemy_catalog.SneakyGremlin()
  return enemy

class TestEffectInterface():
  def test_init_effects_player_debuffs(self, ei):
    output = ei.init_effects("player debuffs")
    assert "Vulnerable" in output

  def test_init_effects_player_buffs(self, ei):
    output = ei.init_effects("player buffs")
    assert "Amplify" in output

  def test_init_effects_enemy_debuffs(self, ei):
    output = ei.init_effects("enemy debuffs")
    assert "Choked" in output

  def test_init_effects_enemy_buffs(self, ei):
    output = ei.init_effects("enemy buffs")
    assert "Sharp Hide" in output

class TestApplyEffects():
  def test_player_buffs(self, ei, player):
    buffs = ei.init_effects("player buffs")
    for buff in buffs:
      ei.apply_effect(target=player, user=player,
                      effect_name=buff, amount=random.randint(1, 5))
    # No easy asserts possible
    for tick in range(random.randint(2, 7)):
      print(f"Tick: {tick+1}")
      ei.tick_effects(player)

  def test_enemy_buffs(self, ei, enemy):
    buffs = ei.init_effects("enemy buffs")
    for buff in buffs:
      ei.apply_effect(target=enemy, user=enemy, effect_name=buff, amount=random.randint(1, 5))
    # No easy asserts possible

  def test_player_debuffs(self, ei, player):
    debuffs = ei.init_effects("player debuffs")
    for debuff in debuffs:
      ei.apply_effect(target=player, user=player, effect_name=debuff, amount=random.randint(1, 5))
    # No easy asserts possible

  def test_enemy_debuffs(self, ei, enemy):
    debuffs = ei.init_effects("enemy debuffs")
    for debuff in debuffs:
      ei.apply_effect(target=enemy, user=enemy, effect_name=debuff, amount=random.randint(1, 5))
    # No easy asserts possible