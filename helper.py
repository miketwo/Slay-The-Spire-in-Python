from __future__ import annotations

import math
import random
from os import name, system
from time import sleep
from typing import TYPE_CHECKING, Callable

from ansi_tags import ansiprint, strip
from definitions import (
    CardType,
    CombatTier,
    EffectType,
    PlayerClass,
    Rarity,
    StackType,
    State,
)
from message_bus_tools import Effect, Message, bus

if TYPE_CHECKING:
    from entities import Enemy, Player, PendingAction
    from items import Card


def get_attribute(item, attribute):
    '''While refactoring, some items (Cards) have properties that are on the object, whereas others have them in a dictionary.
        This function bridges the difference.
    '''
    if isinstance(item, dict):
        return item[attribute]
    else:
        return getattr(item, attribute.lower())


class Displayer:
    """Displays important info to the player during combat"""

    def __init__(self):
        pass

    def view_piles(self, pile: list[Card], shuffle=False, end=False, validator: Callable = lambda placehold: bool(placehold)):
        """Prints a numbered list of all the cards in a certain pile."""
        if len(pile) == 0:
            ansiprint("<red>This pile is empty</red>.")
            sleep(1.5)
            self.clear()
            return
        if shuffle is True:
            pile = random.sample(pile, len(pile))
            ansiprint("<italic>Cards are not shown in order.</italic>")
        counter = 1
        for card in pile:
            if validator(card):
                ansiprint(f"{counter}: {card.pretty_print()}")
                counter += 1
                sleep(0.05)
            else:
                ansiprint(f"{counter}: <light-black>{strip(card.pretty_print())}</light-black>")
                counter += 1
                sleep(0.05)
        if end:
            input("Press enter to continue > ")
            sleep(0.5)
            self.clear()

    def view_relics(self, relic_pool, end=False, validator: Callable = lambda placehold: bool(placehold)):
        for relic in relic_pool:
            if validator(relic):
                ansiprint(relic.pretty_print())
                sleep(0.05)
        if end:
            input("Press enter to continue > ")
            sleep(1.5)
            self.clear()

    def view_potions(self, potion_pool, only_the_potions = False, max_potions=3, numbered_list=True, validator: Callable = lambda placehold: bool(placehold)):
        counter = 1
        for potion in potion_pool:
            if validator(potion):
                ansiprint(f'{counter}: ' + potion.pretty_print())
                counter += 1
        if only_the_potions is False:
            for _ in range(max_potions - len(potion_pool)):
                ansiprint(f"<light-black>{f'{counter}: ' if numbered_list else ''}(Empty)</light-black>")
                counter += 1

    def view_map(self, game_map):
        game_map.pretty_print()
        print("\n")
        sleep(0.2)
        input("Press enter to leave > ")

    def display_ui(self, entity, enemies, combat=True):
        # Repeats for every card in the entity's hand
        ansiprint("<bold>Relics: </bold>")
        self.view_relics(entity.relics)
        ansiprint("<bold>Hand: </bold>")
        self.view_piles(pile=entity.hand, shuffle=False, validator=lambda card: (card.energy_cost if card.energy_cost != -1 else entity.energy) <= entity.energy)
        if combat is True:
            counter = 1
            ansiprint("\n<bold>Enemies:</bold>")
            viewable_enemies = [enemy for enemy in enemies if enemy.state in (State.ALIVE, State.INTANGIBLE)]
            for enemy in viewable_enemies:
                ansiprint(f"{counter}: " + repr(enemy))
                counter += 1
            ansiprint("\n" + repr(entity))
        else:
            ansiprint(str(entity))
        print()

    def list_input(self, input_string: str, choices: list, displayer: Callable, validator: Callable = lambda placehold: bool(placehold), message_when_invalid: str = None, extra_allowables=None) -> int | None:
        """Allows the player to choose from a certain list of options. Includes validation."""
        if extra_allowables is None:
            extra_allowables = []
        if len(choices) == 0:
            ansiprint("<red>There are no choices to choose from.</red>")
            sleep(1.5)
            return None
        while True:
            try:
                displayer(choices, validator=validator)
                ansiprint(input_string + " > ", end="")
                response = input()
                if response in extra_allowables:
                    return response
                option = int(response) - 1
                if not validator(choices[option]):

                    ansiprint(f"\n<red>{message_when_invalid}</red>")
                    sleep(1.5)
                    continue
            except (IndexError, ValueError):
                ansiprint(f"\n<red>You have to enter a whole number between 1 and {len(choices)}.</red>")
                sleep(1)
                continue
            break
        return option

    def multi_input(self, input_string: str, choices: list, displayer: Callable, max_choices: int, strict: bool = False, validator: Callable = lambda placehold: bool(placehold), message_when_invalid: str = None, extra_allowables: list=None):
        """Basically the same as view.list_input but you can choose multiple cards one at a time. Mainly used for discarding and Exhausting cards."""
        if not extra_allowables:
            extra_allowables = []
        finished = False
        to_be_moved = []
        while not finished:
            while True and len(choices) > 0:
                try:
                    displayer(choices, validator=validator)
                    ansiprint(input_string + "(type 'exit' to finish) > ", end="")
                    response = input()
                    if response == 'exit' and (strict and len(to_be_moved) < max_choices):
                        ansiprint(f"<red>You have to choose exactly {max_choices} items.</red>")
                        sleep(1)
                        continue
                    elif response == 'exit':
                        finished = True
                        break
                    if response in extra_allowables:
                        return response
                    option = int(response) - 1
                    if not validator(choices[option]):
                        ansiprint(f"<red>{message_when_invalid}</red>")
                        sleep(1.5)
                        continue
                    if len(to_be_moved) == max_choices:
                        del to_be_moved[0]
                except (IndexError, ValueError):
                    ansiprint(f"<red>You have to enter a whole number between 1 and {len(choices)}.</red>")
                    sleep(1)
                    continue
                to_be_moved.append(choices[option])
                break

    def clear(self):
        system("cls" if name == "nt" else "clear")


class Generators:
    """Generates relic_pool, potions, and cards"""

    def __init__(self):
        pass

    def generate_card_rewards(self, reward_tier: CombatTier, amount: int, entity: object, card_pool: dict) -> list[dict]:
        """
        Normal combat rewards:
        Rare: 3% | Uncommon: 37% | Common: 60%

        Elite combat rewards:
        Rare: 10% | Uncommon: 40% | Common: 50%

        Boss combat rewards:
        Rare: 100% | Uncommon: 0% | Common: 0%
        """
        common_cards = [card for card in card_pool if card.rarity == Rarity.COMMON and card.type not in (CardType.STATUS, CardType.CURSE) and card.player_class == entity.player_class]
        uncommon_cards = [card for card in card_pool if card.rarity == Rarity.UNCOMMON and card.type not in (CardType.STATUS, CardType.CURSE) and card.player_class == entity.player_class]
        rare_cards = [card for card in card_pool if card.rarity == Rarity.RARE and card.type not in (CardType.STATUS, CardType.CURSE) and card.player_class == entity.player_class]
        assert len(common_cards) > 0, "Common pool is empty."
        assert len(uncommon_cards) > 0, "Uncommon pool is empty."
        assert len(rare_cards) > 0, "Rare pool is empty."

        rarities = [common_cards, uncommon_cards, rare_cards]
        rewards = []
        if reward_tier == CombatTier.NORMAL:
            chances = [0.60, 0.37, 0.03]
        elif reward_tier == CombatTier.ELITE:
            chances = [0.5, 0.4, 0.1]
        elif reward_tier == CombatTier.BOSS:
            chances = [0, 0, 1]
        for _ in range(amount):
            chosen_pool = random.choices(rarities, chances, k=1)[0]
            rewards.append(random.choice(chosen_pool))
        return rewards

    def generate_potion_rewards(self, amount: int, entity: object, potion_pool: dict, chance_based=True) -> list[dict]:
        """You have a 40% chance to get a potion at the end of combat.
        -10% when you get a potion.
        +10% when you don't get a potion."""
        common_potions: list[dict] = [potion for potion in potion_pool if potion.rarity == Rarity.COMMON and (potion.player_class == PlayerClass.ANY or potion.player_class == entity.player_class)]
        uncommon_potions: list[dict] = [potion for potion in potion_pool if potion.rarity == Rarity.UNCOMMON and (potion.player_class == PlayerClass.ANY or potion.player_class == entity.player_class)]
        rare_potions: list[dict] = [potion for potion in potion_pool if potion.rarity == Rarity.RARE and (potion.player_class == PlayerClass.ANY or potion.player_class == entity.player_class)]
        assert len(common_potions) > 0, "Common potions pool is empty."
        assert len(uncommon_potions) > 0, "Uncommon potions pool is empty."
        assert len(rare_potions) > 0, "Rare potions pool is empty."

        all_potions = common_potions + uncommon_potions + rare_potions
        rarities = [common_potions, uncommon_potions, rare_potions]
        rewards = []
        for _ in range(amount):
            if chance_based:
                rewards.append(random.choice(random.choices(rarities, [0.65, 0.25, 0.1], k=1)[0]))
            else:
                rewards.append(random.choice(all_potions))
        return rewards

    def generate_relic_rewards(self, source: str, amount: int, entity, relic_pool: dict, chance_based=True) -> list[dict]:
        claimed_relics = [relic.name for relic in entity.relics]

        common_relics = [relic for relic in relic_pool if relic.rarity == Rarity.COMMON and relic.player_class == entity.player_class and relic not in entity.relics and relic.name not in claimed_relics]
        uncommon_relics = [relic for relic in relic_pool if relic.rarity == Rarity.UNCOMMON and relic.player_class == entity.player_class and relic not in entity.relics and relic.name not in claimed_relics]
        rare_relics = [relic for relic in relic_pool if relic.rarity == Rarity.RARE and relic.player_class == entity.player_class and relic not in entity.relics and relic.name not in claimed_relics]

        all_relic_pool = common_relics + uncommon_relics + rare_relics
        rarities = [common_relics, uncommon_relics, rare_relics]

        assert len(common_relics) > 0, "Common relics pool is empty."
        assert len(uncommon_relics) > 0, "Uncommon relics pool is empty."
        assert len(rare_relics) > 0, "Rare relics pool is empty."

        rewards = []
        if source == "Chest":
            percent_common = 0.49
            percent_uncommon = 0.42
            percent_rare = 0.09
        else:
            percent_common = 0.50
            percent_uncommon = 0.33
            percent_rare = 0.17
        for _ in range(amount):
            if chance_based:
                rewards.append(random.choice(random.choices(rarities, [percent_common, percent_uncommon, percent_rare], k=1)[0]))
            else:
                rewards.append(random.choice(all_relic_pool))
        return rewards

    def claim_relics(self, choice: bool, entity: object, relic_amount: int, relic_pool: dict = None, rewards: list = None, chance_based=True):
        relic_pool = relic_pool if relic_pool else relic_pool
        if not rewards:
            rewards = self.generate_relic_rewards("Other", relic_amount, entity, relic_pool, chance_based)
        if not choice:
            for i in range(relic_amount):
                entity.relics.append(rewards[i])
                entity.on_relic_pickup(rewards[i])
                ansiprint(f"{entity.name} obtained {rewards[i].name}.")
                rewards.remove(rewards[i])
                sleep(0.5)
            sleep(0.5)
        while len(rewards) > 0 and choice:
            option = view.list_input("Choose a relic", rewards, view.view_relics)
            if not option:
                sleep(1.5)
                view.clear()
                continue
            entity.relics.append(rewards[option])
            bus.publish(Message.ON_RELIC_ADD, (rewards[option], entity))
            print(f"{entity.name} obtained {rewards[option].name}.")
            rewards.remove(rewards[i])

    def claim_potions(self, choice: bool, potion_amount: int, entity, potion_pool: dict, rewards=None, chance_based=True):
        for relic in entity.relics:
            if relic.name == "Sozu":
                return
        if not rewards:
            rewards = self.generate_potion_rewards(potion_amount, entity, potion_pool, chance_based)
        if not choice:
            for i in range(potion_amount):
                if len(entity.potions) <= entity.max_potions:
                    entity.potions.append(rewards[i])
                    print(f"{entity.name} obtained {rewards[i].name} | {rewards[i].info}")
                    rewards.remove(rewards[i])
            sleep(1)
            view.clear()
        while len(rewards) > 0:
            print(f"Potion Bag: ({len(potion_pool)} / {entity.max_potions})")
            view.view_potions(entity.potions)
            print()
            print("Potion reward(s):")
            option = view.list_input("Choose a potion", rewards, lambda potion_pool, validator: view.view_potions(potion_pool, True, validator=validator))
            if len(potion_pool) == entity.max_potions:
                ansiprint("<red>Potion bag full!</red>")
                sleep(0.5)
                option = input("Discard a potion?(y|n) > ")
                if option == "y":
                    option = view.list_input("Choose a potion to discard", entity.potions, view.view_potions,)
                    print(f"Discarded {entity.potions[option]['Name']}.")
                    del entity.potions[option]
                    sleep(1)
                    view.clear()
                else:
                    sleep(1)
                    view.clear()
                continue
            entity.potions.append(rewards.pop(option))
            sleep(0.2)
            view.clear()

    def card_rewards(self, tier: str, choice: bool, entity, card_pool: dict, rewards=None):
        if not rewards:
            rewards = self.generate_card_rewards(tier, entity.card_reward_choices, entity, card_pool)
        while True:
            if choice:
                chosen_reward = view.list_input("Choose a card", rewards, view.view_piles)
                if (
                    entity.upgrade_attacks and rewards[chosen_reward].type == CardType.ATTACK
                    or (entity.upgrade_skills and rewards[chosen_reward].type == CardType.SKILL
                    or entity.upgrade_powers and rewards[chosen_reward].type == CardType.POWER
                )):
                    rewards[chosen_reward].upgrade()
                entity.deck.append(rewards[chosen_reward])
                ansiprint(f"{entity.name} obtained <bold>{rewards[chosen_reward].name}</bold>")
                rewards.clear()
                break
            for card in rewards:
                bus.publish(Message.ON_CARD_ADD, (entity, card))
                entity.deck.append(card)
                print(f"{entity.name} obtained {card.name}")
                rewards.remove(card)
            break
        rewards.clear()
        sleep(1)


class Strength(Effect):
    registers = [Message.BEFORE_ATTACK]
    def __init__(self, host, amount):
        super().__init__(host, 'Strength', StackType.INTENSITY, EffectType.BUFF, "Increases attack damage by X.", amount)

    def callback(self, message, data):
        if message == Message.BEFORE_ATTACK:
            attacker, target, damage_dealer = data
            if self.host == attacker:
                damage_dealer.modify_damage(self.amount, f"<buff>Strength</buff>({self.amount:+d} dmg)")
            elif self.host == target:
                pass # The target has the Strength effect
            else:
                pass # Neither attacker nor target has the Strength effect

class StrengthDown(Effect):
    registers = [Message.END_OF_TURN]
    def __init__(self, host, amount):
        super().__init__(host, 'Strength Down', StackType.INTENSITY, EffectType.DEBUFF, "At the end of your turn, lose X <buff>Strength</buff>.", amount, one_turn=True)

    def callback(self, message, data):
        if message == Message.END_OF_TURN:
            player, _ = data
            ei.apply_effect(player, None, Strength, -self.amount)

class Vulnerable(Effect):
    registers = [Message.BEFORE_ATTACK]
    def __init__(self, host, amount):
        super().__init__(host, 'Vulnerable', StackType.DURATION, EffectType.DEBUFF, "Target takes 50% more damage from attacks.", amount)

    def callback(self, message, data):
        if message == Message.BEFORE_ATTACK:
            attacker, target, damage_dealer = data
            if self.host == attacker:
                pass # The attacker is the one with the Vulnerable effect
            elif self.host == target:
                damage_dealer.modify_damage(math.floor(damage_dealer.damage * 0.5), "<debuff>Vulnerable</debuff>(x1.5 dmg)")
            else:
                pass # Neither attacker nor target has the Vulnerable effect

class Weak(Effect):
    registers = [Message.BEFORE_ATTACK]
    def __init__(self, host, amount):
        super().__init__(host, 'Weak', StackType.DURATION, EffectType.DEBUFF, "Target deals 25% less attack damage.", amount)

    def callback(self, message, data):
        if message == Message.BEFORE_ATTACK:
            attacker, target, damage_dealer = data
            if self.host == attacker:
                damage_dealer.modify_damage(-math.floor(damage_dealer.damage * 0.25), "<debuff>Weak</debuff>(x0.75 dmg)")
            elif self.host == target:
                pass
            else:
                pass

class Frail(Effect):
    registers = [Message.BEFORE_BLOCK]
    def __init__(self, host, amount):
        super().__init__(host, 'Frail', StackType.DURATION, EffectType.DEBUFF, "You gain 25% less <keyword>Block</keyword> from cards.", amount)

    def callback(self, message, data):
        if message == Message.BEFORE_BLOCK:
            _, card = data
            if card is not None:
                card.modify_block(-math.floor(card.block * 0.25), "<debuff>Frail</debuff>(x0.75 block)")

class CurlUp(Effect):
    registers = [Message.ON_ATTACKED]
    def __init__(self, host, amount):
        # INFO: Due to some very strange bug, the 'C' is interpreted as the end of an escape sequence(^[[?62;4C) which is why it's escaped. wtf
        super().__init__(host, 'Curl Up', StackType.INTENSITY, EffectType.BUFF, "On recieving attack damage, rolls and gains X <keyword>Block</keyword>. (Once per combat)", amount)  # noqa: W605

    def callback(self, message, data):
        if message == Message.ON_ATTACKED:
            target = data
            if target != self.host:
                return
            target.blocking(block=self.amount, context=self.name)
            self.amount = 0

class Ritual(Effect):
    registers = [Message.END_OF_TURN]
    def __init__(self, host, amount):
        super().__init__(host, "Ritual", StackType.INTENSITY, EffectType.BUFF, "At the end of its turn, gains X <buff>Strength</buff>.", amount)

    def callback(self, message, data):
        if message == Message.END_OF_TURN:
            _ = data
            ei.apply_effect(self.host, None, Strength, self.amount)

class Enrage(Effect):
    registers = [Message.ON_CARD_PLAY]
    def __init__(self, host, amount):
        super().__init__(host, "Enrage", StackType.INTENSITY, EffectType.BUFF, "Whenever you play a Skill, gains X  Strength..", amount)

    def callback(self, message, data):
        if message == Message.ON_CARD_PLAY:
            origin, card, target, enemies = data
            if card.type == CardType.SKILL:
                ei.apply_effect(origin, None, Strength, self.amount)

class Corruption(Effect):
    registers = [Message.ON_CARD_PLAY]
    def __init__(self, host, amount):
        super().__init__(host, "Corruption", StackType.INTENSITY, EffectType.BUFF, "Whenever you play a Skill, exhaust it.", amount)

    def callback(self, message, data):
        if message == Message.ON_CARD_PLAY:
            origin, card, target, enemies = data
            if card.type == CardType.SKILL:
                # TODO: Exhaust the card
                pass

class NoDraw(Effect):
    registers = [Message.BEFORE_DRAW, Message.END_OF_TURN]

    def __init__(self, host, _):
        super().__init__(host, "No Draw", StackType.NONE, EffectType.DEBUFF, "You may not draw any more cards this turn.")

    def callback(self, message, data: tuple[Player, PendingAction]):
        if message == Message.BEFORE_DRAW:
            player, action = data
            ansiprint(f"{player.name} cannot draw any more cards because of <debuff>No Draw</debuff>.")
            action.cancel(reason="You cannot draw any cards because of <debuff>No Draw</debuff>.")
        if message == Message.END_OF_TURN:
            self.unsubscribe()

class Combust(Effect):
    registers = [Message.END_OF_TURN]
    def __init__(self, host, amount):
        super().__init__(host, "Combust", StackType.INTENSITY, EffectType.BUFF, "At the end of your turn, deals X damage to ALL enemies.", amount)

    def callback(self, message, data: tuple[Player, list[Enemy]]):
        if message == Message.END_OF_TURN:
            player, enemies = data
            for enemy in enemies:
                enemy.health -= self.amount

class DarkEmbrace(Effect):
    registers = [Message.ON_EXHAUST]
    def __init__(self, target, amount=1):
        # "Whenever a card is <keyword>Exhausted</keyword>, draw 1 card
        super().__init__(None, name="Dark Embrace", stack_type=StackType.NONE, effect_type=EffectType.BUFF, info="Whenever a card is <keyword>Exhausted</keyword>, draw 1 card.", amount=amount)

    def callback(self, message, data: tuple[Player, Card]):
        if message == Message.END_OF_TURN:
            player, card = data
            player.draw_cards(self.amount)

class Evolve(Effect):
    registers = [Message.ON_CARD_PLAY]
    def __init__(self, host, amount):
        super().__init__(host, "Evolve", StackType.NONE, EffectType.BUFF, "Whenever you play a Status or Curse, draw 1 card.", amount)

    def callback(self, message, data: tuple[Player, Card, Enemy]):
        if message == Message.ON_CARD_PLAY:
            origin, card, target, enemies = data
            if card.type in (CardType.STATUS, CardType.CURSE):
                origin.draw_cards(1)

class FeelNoPain(Effect):
    registers = [Message.ON_CARD_PLAY]
    def __init__(self, host, amount):
        super().__init__(host, "Feel No Pain", StackType.INTENSITY, EffectType.BUFF, "Whenever you play a Skill, gain X <keyword>Block</keyword>.", amount)

    def callback(self, message, data):
        if message == Message.ON_CARD_PLAY:
            origin, card, target, enemies = data
            if card.type == CardType.SKILL:
                origin.blocking(block=self.amount, context=self.name)

class FireBreathing(Effect):
    registers = [Message.ON_CARD_PLAY]
    def __init__(self, host, amount):
        super().__init__(host, "Fire Breathing", StackType.INTENSITY, EffectType.BUFF, "Whenever you play an Attack, deal X damage to ALL enemies.", amount)

    def callback(self, message, data: tuple[Player, Card, Enemy, list[Enemy]]):
        if message == Message.ON_CARD_PLAY:
            player, card, target, enemies = data
            if card.type == CardType.ATTACK:
                for enemy in enemies:
                    enemy.health -= self.amount
                    ansiprint(f"{enemy.name} took {self.amount} damage from <buff>Fire Breathing</buff>.")

class FlameBarrier(Effect):
    # "Gain 12 <keyword>Block</keyword>. Whenever you're attacked this turn, deal 4 damage back."
    registers = [Message.ON_ATTACKED]

    def __init__(self, host, amount):
        super().__init__(host, "Flame Barrier", StackType.NONE, EffectType.BUFF, "Gain 12 <keyword>Block</keyword>. Whenever you're attacked this turn, deal 4 damage back.", amount)

    def callback(self, message, data):
        if message == Message.ON_ATTACKED:
            target = data
            target.health -= 4


class Metallicize(Effect):
    registers = [Message.END_OF_TURN]

    def __init__(self, host, amount=3):
        super().__init__(host, "Metallicize", StackType.INTENSITY, EffectType.BUFF, "At the end of your turn, gain 3 <keyword>Block</keyword>.", amount, one_turn=True)

    def callback(self, message, data: tuple[Player, list[Enemy]]):
        if message == Message.END_OF_TURN:
            player, enemies = data
            player.blocking(block=self.amount, context=f"{self.name}{self.amount}")


class Rage(Effect):
    #"Whenever you play an <keyword>Attack</keyword> this turn, gain 3 <keyword>Block</keyword>.""
    registers = [Message.ON_CARD_PLAY, Message.END_OF_TURN]

    def __init__(self, host, amount=3):
        super().__init__(host, "Rage", StackType.NONE, EffectType.BUFF, "Whenever you play an <keyword>Attack</keyword> this turn, gain 3 <keyword>Block</keyword>.", amount=amount)

    def callback(self, message, data):
        if message == Message.ON_CARD_PLAY:
            player, card, target, enemies = data
            if card.type == CardType.ATTACK:
                player.blocking(block=self.amount, context=self.name)
        elif message == Message.END_OF_TURN:
            self.unsubscribe()

class Barricade(Effect):
    # "Barricade", "<keyword>Block</keyword> is not removed at the start of your turn."
    registers = [Message.BEFORE_BLOCK, Message.END_OF_TURN]

    def __init__(self, host, amount=0):
        super().__init__(host, "Barricade", StackType.NONE, EffectType.BUFF, "<keyword>Block</keyword> is not removed at the start of your turn.", amount)
        self.end_of_turn_block = None

    def callback(self, message, data: tuple[Player, PendingAction] | tuple[Player, list[Enemy]]):
        if message == Message.END_OF_TURN:
            player, enemies = data
            self.end_of_turn_block = player.block
        elif message == Message.BEFORE_BLOCK and self.end_of_turn_block is not None:
            player, action = data
            action.set_amount(self.end_of_turn_block)
            self.unsubscribe()

class Berzerk(Effect):
    #"Gain 2 <debuff>Vulnerable</debuff>. At the start of your turn, gain 1 <keyword>Energy</keyword>."
    registers = [Message.START_OF_TURN]

    def __init__(self, host, amount=2):
        super().__init__(host, "Berzerk", StackType.NONE, EffectType.BUFF, "Gain 2 <debuff>Vulnerable</debuff>. At the start of your turn, gain 1 <keyword>Energy</keyword>.", amount)

    def callback(self, message, data: tuple[int, Player]):
        if message == Message.START_OF_TURN:
            turn, player = data
            player.energy += 1


class Brutality(Effect):
    # "At the start of your turn, lose 1 HP and draw 1 card."
    registers = [Message.START_OF_TURN]

    def __init__(self, host, amount=1):
        super().__init__(host, "Brutality", StackType.NONE, EffectType.BUFF, "At the start of your turn, lose 1 HP and draw 1 card.", amount=amount)

    def callback(self, message, data: tuple[int, Player]):
        if message == Message.START_OF_TURN:
            turn, player = data
            player.take_sourceless_dmg(1)
            player.draw_cards(1)

class Split(Effect):
    # When activated, splits into two smaller enemies.
    registers = [Message.ON_DEATH_OR_ESCAPE]

    def __init__(self, host, amount=0):
        super().__init__(host, "Split", StackType.NONE, EffectType.BUFF, "When activated, splits into two smaller enemies.", amount=amount)

    def callback(self, message, data: tuple[Enemy, list[Enemy]]):
        if message == Message.ON_DEATH_OR_ESCAPE:
            print("Split effect activated")
            enemy, enemies = data
            split_into = {
                "Slime Boss": (
                    Enemy(self.health, 0, "Acid Slime(L)"),
                    Enemy(self.health, 0, "Spike Slime (L)"),
                ),
                "Acid Slime (L)": (
                    Enemy(self.health, 0, "Acid Slime(M)"),
                    Enemy(self.health, 0, "Acid Slime(M)"),
                ),
                "Spike Slime (L)": (
                    Enemy(self.health, 0, "Spike Slime (M)"),
                    Enemy(self.health, 0, "Spike Slime (M)"),
                ),
            }
            if enemy.name in split_into:
                enemy.health = 0
                for new_enemy in split_into[enemy.name]:
                    new_enemy.health = enemy.max_health // 2
                    enemies.append(new_enemy)
                del enemies[enemies.index(enemy)]
                ansiprint(f"{self.name} split into 2 {split_into[self.name].name}s")


class Artifact(Effect):
    ''' Artifact is a buff that will negate the next Debuff on that unit.

    Each stack of Icon Artifact Artifact can block 1 application of a Debuff. For example:

    Bouncing Flask will remove 1 Icon Artifact Artifact with each bounce.
    Envenom will remove 1 Icon Artifact Artifact with each unblocked Attack damage.
    Shockwave and Crippling Cloud will remove up to 2 Icon Artifact Artifacts from each enemy, since they inflict 2 Debuffs.
    Effects that apply multiple Debuffs will do so in the order listed on the card. For instance, if an enemy has 1 Icon Artifact Artifact and is hit by Shockwave, the card will apply Icon Weak Weak then apply Icon Vulnerable Vulnerable as per its description, and the enemy will lose 1 Icon Artifact Artifact to negate Icon Weak Weak and only has Icon Vulnerable Vulnerable inflicted on it.'''
    registers = [Message.BEFORE_APPLY_EFFECT]

    def __init__(self, host, amount=1):
        super().__init__(host, "Artifact", StackType.INTENSITY, EffectType.BUFF, "Negates the next Debuff on the target.", amount=amount)

    def callback(self, message, data: tuple[Effect, Player, Player]):
        if message == Message.BEFORE_APPLY_EFFECT:
            print("Artifact effect activated")
            effect, target, user = data
            if effect.type == EffectType.DEBUFF and self.amount > 0:
                effect.unsubscribe()
                self.amount -= 1
                ansiprint(f"{target.name} blocked {effect.name} with <buff>Artifact</buff>.")
                return False
            return True

class Asleep(Effect):
    # The Lagavulin will start with the unique debuff "Asleep", as well as a Icon Metallicize Metallicize buff, preventing it from taking any action, but granting it 8 Icon Block Block at the start of every turn. The Lagavulin will awake at the end of its 3rd turn or when any HP damage is taken through the Icon Block Block, and will lose its Icon Metallicize Metallicize buff in the process.
    # When the Lagavulin wakes up by being attacked, it will be stunned for one turn. If the Lagavulin is left unharmed for three turns, it will wake up on its own and begin the fourth turn unstunned.
    registers = [Message.START_OF_TURN, Message.ON_ATTACKED]

    def __init__(self, host: Enemy, amount=3):
        super().__init__(host, "Asleep", StackType.NONE, EffectType.DEBUFF, "Prevents the enemy from taking any action.", amount=amount)

    def callback(self, message, data: Enemy):
        if message == Message.START_OF_TURN:
            if self.amount > 0:
                ei.apply_effect(self.host, None, Metallicize, 8)
        elif message == Message.ON_ATTACKED:
            target = data
            self.host.debuffs.append(Stunned(self.host, 1))

class Stunned(Effect):
    # Stunned is a debuff that prevents the target from taking any action for a certain number of turns.
    registers = [Message.AFTER_SET_INTENT]

    def __init__(self, host, amount=1):
        super().__init__(host, "Stunned", StackType.NONE, EffectType.DEBUFF, "Prevents the target from taking any action.", amount=amount)

    def callback(self, message, data: PendingAction):
        if message == Message.AFTER_SET_INTENT:
            print("TBD: Stunned Effect")

class Dexterity(Effect):
    # Dexterity is a buff that increases the amount of Block gained from cards.
    registers = [Message.BEFORE_BLOCK]

    def __init__(self, host, amount):
        super().__init__(host, "Dexterity", StackType.INTENSITY, EffectType.BUFF, "Increases the amount of Block gained from cards.", amount)

    def callback(self, message, data: tuple[Player, Card]):
        if message == Message.BEFORE_BLOCK:
            player, card = data
            if card is not None:
                card.modify_block(self.amount, f"<buff>Dexterity</buff>({self.amount:+d} block)", permanent=False)


class SporeCloud(Effect):
    # On death, applies X Icon Vulnerable Vulnerable to the player.
    registers = [Message.ON_DEATH_OR_ESCAPE]

    def __init__(self, host, amount=2):
        super().__init__(host, "Spore Cloud", StackType.NONE, EffectType.DEBUFF, "On death, applies X Icon Vulnerable Vulnerable to the player.", amount=amount)

    def callback(self, message, data: tuple[Enemy, list[Enemy]]):
        if message == Message.ON_DEATH_OR_ESCAPE:
            player, _ = data
            ei.apply_effect(player, None, Vulnerable, self.amount)


class Thievery(Effect):
    # X Gold is stolen with every attack. Total Gold stolen is returned if the enemy is killed.
    registers = [Message.AFTER_ATTACK, Message.ON_DEATH_OR_ESCAPE]

    def __init__(self, host, amount=15):
        super().__init__(host, "Thievery", StackType.NONE, EffectType.DEBUFF, "X Gold is stolen with every attack. Total Gold stolen is returned if the enemy is killed.", amount=amount)
        self.stolen_gold = 0

    def callback(self, message, data: tuple[Player, int] | tuple[Enemy, list[Enemy]]):
        if message == Message.AFTER_ATTACK:
            attacker, target, dmg = data
            if attacker == self.host:
                target.gold -= self.amount
                self.stolen_gold += self.amount
                ansiprint(f"{attacker.name} stole {self.amount} gold from {target.name}.")
        elif message == Message.ON_DEATH_OR_ESCAPE:
            player, enemies, dead_entity = data
            if dead_entity == self.host:
                player.gold += self.stolen_gold
                ansiprint(f"{player.name} received {self.stolen_gold} gold from {self.host.name}.")

class Angry(Effect):
    # Increases Strength by X when taking attack damage.
    registers = [Message.AFTER_ATTACK]

    def __init__(self, host, amount=1):
        super().__init__(host, "Angry", StackType.INTENSITY, EffectType.BUFF, "Increases Strength by X when taking attack damage.", amount=amount)

    def callback(self, message, data: tuple[Player, Enemy, int]):
        if message == Message.AFTER_ATTACK:
            attacker, target, dmg = data
            if target == self.host:
                ei.apply_effect(self.host, None, Strength, self.amount)


class EffectInterface:
    """Responsible for applying effects, creating buff/debuff dictionaries, and counting down certain effects"""
    def __init__(self):
        pass

    def apply_effect(self, target, user, effect, amount=0, recursion_tag=False) -> None:
        """recurstion_tag is only meant for internal use to stop infinite loops with Champion Belt."""
        # HACK HACK HACK Dynamically search for the effect class if it's a string. This is icky and should be avoided.
        if isinstance(effect, str) and effect in globals():
            effect = globals()[effect]
        assert isinstance(effect, type(Effect)), f"Effect must be an Effect class. You passed {effect} (type: {type(effect)})."
        current_relic_pool = (
            [relic.name for relic in user.relics]
            if getattr(user, "player_class", "placehold") in str(user)
            else []
        )
        effect = effect(target, amount)
        effect_type = EffectType.DEBUFF if effect.amount < 0 else effect.type
        if str(user) == "Player" and effect in ("Weak", "Frail"):
            if "Turnip" in current_relic_pool and effect.name == "Frail":
                ansiprint("<debuff>Frail</debuff> was blocked by your <bold>Turnip</bold>.")
            elif "Ginger" in current_relic_pool and effect.name == "Weak":
                ansiprint("<debuff>Weak</debuff> was blocked by <bold>Ginger</bold>")
            return
        if effect_type == EffectType.DEBUFF and "Artifact" in current_relic_pool: # TODO: Make Artifact buff.
            subject = getattr(target, "third_person_ref", "Your")
            ansiprint(f"<debuff>{effect.name}</debuff> was blocked by {subject} <buff>Artifact</buff>.")
        else:
            effect.register(bus)
            if effect_type == EffectType.DEBUFF:
                target.debuffs.append(effect)
                target.debuffs = self.merge_duplicates(target.debuffs)
            else:
                target.buffs.append(effect)
                target.buffs = self.merge_duplicates(target.buffs)

            if 'Player' in str(target) and user is None:
                # If the player applied an effect to themselves
                ansiprint(f"You gained {effect.get_name()}")
            elif ('Enemy' in str(target) and user is None) or (target == user and 'Enemy' in str(target)):
                # If the enemy applied an effect to itself
                ansiprint(f"{target.name} gained {effect.get_name()}")
            elif 'Enemy' in str(user) and 'Player' in str(target):
                # If the enemy applied an effect to you
                ansiprint(f"{user.name} applied {effect.get_name()} to you.")
            elif 'Player' in str(user) and 'Enemy' in str(target):
                # If the player applied an effect to the enemy
                ansiprint(f"You applied {effect.get_name()} to {target.name}")
            elif 'Enemy' in str(user) and 'Enemy' in str(target) and user != target:
                # If the enemy applied an effect to another enemy
                ansiprint(f"{user.name} applied {effect.get_name()} to {target.name}.")

            if ("Champion Belt" in current_relic_pool and "Player" in str(user) and not recursion_tag):
                self.apply_effect(target, user, "Weak", 1, True)
            if 'Enemy' in str(user) and hasattr(target, "fresh_effects"):
                target.fresh_effects.append(effect)

    def tick_effects(self, subject):
        for buff in subject.buffs:
            buff.tick()
        for debuff in subject.debuffs:
            debuff.tick()
        def clean(effect):
            if effect.amount >= 1:
                return True
            else:
                effect.unsubscribe()
                return False
        subject.buffs = list(filter(clean, subject.buffs))
        subject.debuffs = list(filter(clean, subject.debuffs))

    def merge_duplicates(self, effect_list):
        # Thank you Claude Sonnet
        result = []
        seen = {}

        for effect in effect_list:
            if effect.name in seen:
                seen[effect.name] += effect
            else:
                seen[effect.name] = effect
                result.append(effect)

        return [seen[effect.name] for effect in result]

    def full_view(self, entity, enemies):
        ansiprint(f"<bold>{entity.name}</bold>")
        for effect in entity.buffs + entity.debuffs:
            ansiprint(effect.pretty_print())
        for enemy in enemies:
            ansiprint(f"<bold>{enemy.name}</bold>:")
            for effect in enemy.buffs + enemy.debuffs:
                ansiprint(effect.pretty_print())


ei = EffectInterface()
gen = Generators()
view = Displayer()
