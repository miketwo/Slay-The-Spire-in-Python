from __future__ import annotations
import math
import random
import sys
from copy import deepcopy
from time import sleep
from uuid import uuid4

import helper
import items
from ansi_tags import ansiprint
from definitions import CardType, State, TargetType
from message_bus_tools import Card, Effect, Message, Potion, Registerable, Relic, bus
from typing import Callable

ei = helper.ei
view = helper.view

class Damage:
    def __init__(self, dmg: int):
        self.damage = dmg
    def modify_damage(self, change: int, context: str, *args, **kwargs):
        new_dmg = self.damage + change
        ansiprint(f"Damage modified from {self.damage} --> {new_dmg} by {context}.")
        self.damage = new_dmg



class PendingAction:
    '''
    A pending action is an action that is created before it is executed. It can be cancelled, modified, and executed.

    '''
    def __init__(self, name: str, action: Callable, amount: int | float):
        self.name = name
        self.action = action
        self.amount = amount
        self.executed = False
        self.cancelled = False
        self.reason = ""

    def cancel(self, reason: str = None):
        self.cancelled = True
        if not reason:
            reason = f"{self.name} was cancelled."
        self.reason = reason

    def set_amount(self, new_amount: int | float):
        self.amount = new_amount

    def increase_amount(self, change: int | float):
        self.amount += change

    def execute(self):
        if self.executed:
            print(f"{self.name} already executed.")
            return
        if self.cancelled:
            ansiprint(self.reason)
            return
        result = self.action(self.amount)
        self.executed = True
        return result

    def __str__(self):
        return f"PendingAction: {self.name}({self.amount})"

    def __repr__(self):
        return self.__str__()


class Player(Registerable):
    """
    Attributes:::
    health: The player's current health
    block: The amount of damage the player can take before losing health. Removed at the start of their turn
    name: The player's name
    player_class: Ironclad, Silent, Defect, and Watcher
    max_health: The max amount health the player can have
    energy: Resource used to play cards. Replenished at the start of their turn
    energy_gain: The base amount of energy the player gains at the start of their turn
    deck: All the cards the player has. Is shuffled into the player's draw pile at the start of combat.
    potions: Holds the potions the player gets.
    max_potions: The max amount of potions the player can have
    """

    registers = [Message.END_OF_COMBAT,
                 Message.START_OF_COMBAT,
                 Message.START_OF_TURN,
                 Message.END_OF_TURN,
                 Message.ON_RELIC_ADD,
                 Message.ON_PLAYER_HEALTH_LOSS]

    def __init__(self, health: int, block: int, max_energy: int, deck: list[Card], powers: list[Effect] = None):
        self.uid = uuid4()
        if not powers:
            powers = []
        self.health: int = health
        self.block: int = block
        self.name: str = "Ironclad"
        self.player_class: str = "Ironclad"
        self.in_combat = False
        self.state = State.ALIVE
        self.floors = 1
        self.fresh_effects: list[str] = []  # Shows what effects were applied after the player's turn
        self.max_health: int = health
        self.energy: int = 0
        self.max_energy: int = max_energy
        self.energy_gain: int = max_energy
        self.deck: list[Card] = deck
        self.potions: list[Potion] = []
        self.relics: list[Relic] = []
        self.max_potions: int = 3
        self.hand: list[Card] = []
        self.draw_pile: list[Card] = []
        self.discard_pile: list[Card] = []
        self.card_reward_choices: int = 3
        self.draw_strength: int = 5
        self.exhaust_pile: list[dict] = []
        self.potion_dropchance = 0.4
        self.orbs = []
        self.orb_slots: int = 3
        self.gold: int = 100
        self.debuffs: list[Effect] = []
        self.buffs: list[Effect] = powers
        # Alternate debuff/buff effects
        self.the_bomb_countdown = 3
        self.deva_energy = 1
        # Relic buffs
        self.pen_nib_attacks: int = 0
        self.ancient_tea_set: bool = False
        self.attacks_played_this_turn: bool = False  # Used for the Art of War relic
        self.taken_damage: bool = False  # Used for the Centennial Puzzle relic
        self.gold_on_card_add: bool = False  # Used for the Ceramic Fish relic
        self.happy_flower: int = 0
        self.block_curses: int = 0  # Used for the Omamori relic
        self.nunckaku_attacks: int = 0
        self.starting_strength: int = 0  # Used for the Red Skull and Vajra relic
        self.golden_bark: bool = False  # Used for the Golden Bark relic
        # Used for the Molten, Toxic, and Frozen Egg relics
        self.upgrade_attacks = False
        self.upgrade_skills = False
        self.upgrade_powers = False
        self.red_skull_active = False
        self.inked_cards = 0  # Used for the Ink Bottle relic
        self.kunai_attacks = 0  # Used for the Kunai relic
        self.letter_opener_skills = 0  # Used for the Letter Opener relic
        self.ornament_fan_attacks = 0  # Used for the Ornamental Fan relic
        self.meat_on_the_bone = False
        self.darkstone_health = False
        self.shuriken_attacks = 0
        self.draw_shuffles = 0  # Used for the Sundial relic
        self.incense_turns = 0  # Used for the Incense Burner relic
        self.girya_charges = 3  # Stores how many times the player can gain Energy from Girya
        self.plays_this_turn = 0  # Counts how many cards the played plays each turn
        self.stone_calender = 0
        self.choker_cards_played = 0  # Used for the Velvet Choker relic

    @classmethod
    def create_player(cls):
        player = cls(health=80, block=0, max_energy=3, deck=[
            items.IroncladStrike(), items.IroncladStrike(), items.IroncladStrike(), items.IroncladStrike(), items.IroncladStrike(),
            items.IroncladDefend(), items.IroncladDefend(), items.IroncladDefend(), items.IroncladDefend(),
            items.Bash()
        ])
        player.relics.append(items.BurningBlood())
        return player


    def __str__(self):
        return f"(<italic>Player</italic>)Ironclad(<red>{self.health} / {self.max_health}</red> | <yellow>{self.gold} Gold</yellow> | Deck: {len(self.deck)})"

    def __repr__(self):
        if self.in_combat is True:
            status = f"\n{self.name} (<red>{self.health} </red>/ <red>{self.max_health}</red> | <light-blue>{self.block} Block</light-blue> | <light-red>{self.energy} / {self.max_energy} Energy</light-red>)"
            for effect in self.buffs + self.debuffs:
                status += " | " + effect.get_name()
        else:
            status = f"\n{self.name} (<red>{self.health} </red>/ <red>{self.max_health}</red> | <yellow>{self.gold} Gold</yellow>)"
        return (
            status + ""
            if status == f"\n{self.name} (<red>{self.health} </red>/ <red>{self.max_health}</red> | <light-blue>{self.block} Block</light-blue> | <light-red>{self.energy} / {self.max_energy}</light-red>)"
            else status + "\n"
        )

    def use_card(self, card, exhaust, pile, enemies, target: "Enemy"=None) -> None:
        """
        Uses a card
        Wow!
        """
        # Determine exhaust status
        if card.type in (CardType.STATUS, CardType.CURSE) and card.name not in ("Slimed", "Pride"):
            if card.type == CardType.CURSE and items.BlueCandle in self.relics:
                exhaust = True
            else:
                return
        if (card.type == CardType.STATUS and "MedicalKit" in self.relics):
            exhaust = True
        elif (card.type == CardType.CURSE and items.BlueCandle in self.relics):
            self.take_sourceless_dmg(1)
            exhaust = True

        # Move the card to the appropriate pile
        if pile is not None:
            if exhaust is True or getattr(card, "exhaust", False) is True:
                ansiprint(f"{card.name} was <bold>Exhausted</bold>.")
                self.move_card(card=card, move_to=self.exhaust_pile, from_location=pile, cost_energy=True)
                bus.publish(Message.ON_EXHAUST, (self, card))
            else:
                self.move_card(card=card, move_to=self.discard_pile, from_location=pile, cost_energy=True)

        # Apply the card's effects
        if card.target == TargetType.SINGLE:
            card.apply(origin=self, target=target)
        elif card.target in (TargetType.AREA, TargetType.ANY):
            card.apply(origin=self, enemies=enemies)
        elif card.target == TargetType.YOURSELF:
            card.apply(origin=self)
        else:
            raise ValueError(f"Invalid target type: {card.target}")
        bus.publish(Message.ON_CARD_PLAY, (self, card, target, enemies))
        sleep(0.5)
        view.clear()

    def draw_cards(self, cards: int = None):
        """Draws [cards] cards from draw pile to hand."""
        if cards is None:
            cards = self.draw_strength
        action = PendingAction(self, self._draw_cards, cards)
        bus.publish(Message.BEFORE_DRAW, (self, action))
        action.execute()
        bus.publish(Message.AFTER_DRAW, (self, action))


    def _draw_cards(self, num_cards: int):
        # Internal function to draw cards
        self.discard_pile.extend(self.hand)
        self.hand.clear()
        if len(self.draw_pile) < num_cards:
            self.draw_pile.extend(random.sample(self.discard_pile, len(self.discard_pile)))
            self.discard_pile = []
            ansiprint("<bold>Discard pile shuffled into draw pile.</bold>")
        self.hand.extend(self.draw_pile[-num_cards:])
        # Removes those cards
        self.draw_pile = self.draw_pile[:-num_cards]
        for card in self.hand:
            card.register(bus=bus)
        print(f"Drew {num_cards} card{'s'[:num_cards^1]}.")  # Cool pluralize hack

    def blocking(self, card: Card = None, block=0, context: str=None):
        """Gains [block] Block. Cards are affected by Dexterity and Frail."""
        bus.publish(Message.BEFORE_BLOCK, (self, card))
        block = getattr(card, 'block', None) if card else block
        block_affected_by = ', '.join(getattr(card, 'block_affected_by', []) if card else [context])
        self.block += block
        ansiprint(f"""{self.name} gained {block} <blue>Block</blue> from {block_affected_by}.""") # f-strings my beloved
        bus.publish(Message.AFTER_BLOCK, (self, card))

    def health_actions(self, heal: int, heal_type: str):
        """If [heal_type] is 'Heal', you heal for [heal] HP. If [heal_type] is 'Max Health', increase your max health by [heal]."""
        heal_type = heal_type.lower()
        if heal_type == "heal":
            self.health += heal
            self.health = min(self.health, self.max_health)
            ansiprint(f"You heal <green>{min(self.max_health - self.health, heal)}</green> <light-blue>HP</light-blue>")
            if (self.health >= math.floor(self.health * 0.5) and any(["Red Skull" in relic.name for relic in self.relics])):
                ansiprint("<red><bold>Red Skull</bold> deactivates</red>.")
                self.starting_strength -= 3
        elif heal_type == "max health":
            self.max_health += heal
            self.health += heal
            ansiprint(f"Your Max HP is {'increased' if heal > 0 else 'decreased'} by <{'light-blue' if heal > 0 else 'red'}>{heal}</{'light-blue' if heal > 0 else 'red'}>")

    def card_actions(self, subject_card: dict, action: str, card_pool: list[dict] = None):
        """[action] == 'Remove', remove [card] from your deck.
        [action] == 'Transform', transform a card into another random card.
        """
        if card_pool is None:
            card_pool = items.create_all_cards()
        while True:
            if action == "Remove":
                del subject_card
            elif action == "Transform":
                # Curse cards can only be transformed into other Curses
                ansiprint(f"{subject_card['Name']} was <bold>transformed</bold> into ", end="")
                if subject_card.get("Type") == "Curse":
                    options = [valid_card for valid_card in items.create_all_cards() if valid_card.get("Type") == "Curse" and valid_card.get("Rarity") != "Special"]
                else:
                    options = [
                        valid_card
                        for valid_card in items.create_all_cards()
                        if valid_card.get("Class") == valid_card.get("Class")
                        and valid_card.get("Type") not in ("Status", "Curse", "Special")
                        and valid_card.get("Upgraded") is not True
                        and valid_card.get("Rarity") != "Basic"
                    ]
                while True:
                    new_card = random.choice(options)
                    if new_card == subject_card:
                        continue
                    ansiprint(f"{new_card['Name']} | <yellow>{new_card['Info']}</yellow>")
                    return new_card
            else:
                raise ValueError(f"Invalid action: {action}")


    def move_card(self, card, move_to, from_location, cost_energy=False, shuffle=False):
        if cost_energy is True:
            self.energy -= max(card.energy_cost, 0)
        if card in from_location:
            from_location.remove(card)
        else:
            ansiprint(f"WARNING: {card.name} was not found in `from_location` in `move_card()` function.")
        if shuffle is True:
            move_to.insert(random.randint(0, len(move_to) - 1), card)
        else:
            move_to.append(card)
        if move_to == self.exhaust_pile:
            bus.publish(Message.ON_EXHAUST, (card))

    def attack(self, target: "Enemy", card: Card=None, dmg=-1):
        # Check if already dead and skip if so
        dmg = getattr(card, 'damage', dmg)
        if target.health <= 0:
            return
        if card is not None and card.type not in (CardType.STATUS, CardType.CURSE):
            bus.publish(Message.BEFORE_ATTACK, (self, target, card))
            dmg = getattr(card, 'damage', dmg)
            if dmg <= target.block:
                target.block -= dmg
                dmg = 0
                ansiprint("<blue>Blocked</blue>")
            elif dmg > target.block:
                dmg -= target.block
                dmg = max(0, dmg)
                target.health -= dmg
                ansiprint(f"You dealt {dmg} damage(<light-blue>{target.block} Blocked</light-blue>) to {target.name} with {' | '.join(card.damage_affected_by)}")
                target.block = 0
                bus.publish(Message.AFTER_ATTACK, (self, target, dmg))
                if target.health <= 0:
                    target.die()
                bus.publish(Message.ON_ATTACKED, (target))

    def gain_gold(self, gold, dialogue=True):
        self.gold += gold
        if dialogue is True:
            ansiprint(f"You gained <green>{gold}</green> <yellow>Gold</yellow>(<yellow>{self.gold}</yellow> Total)")
        sleep(1)

    def take_sourceless_dmg(self, dmg):
        self.health -= dmg
        ansiprint(f"<light-red>You lost {dmg} health.</light-red>")

    def die(self):
        view.clear()
        self.health = max(self.health, 0)
        if items.FairyInABottle() in self.potions:
            try:
                potion_index = self.potions.index(items.FairyInABottle())
            except ValueError:
                potion_index = -1
            self.health_actions(math.floor(self.max_health * self.potions[potion_index].hp_percent), "Heal")
            return
        self.state = State.DEAD
        bus.publish(Message.ON_DEATH_OR_ESCAPE, (self))
        ansiprint("<red>You Died</red>")
        input("Press enter > ")

    def callback(self, message, data: tuple):
        if message == Message.START_OF_COMBAT:
            self.in_combat = True
            self.draw_pile = random.sample(self.deck, len(self.deck))
        elif message == Message.END_OF_COMBAT:
            self.in_combat = False
            self.draw_pile.clear()
            self.discard_pile.clear()
            self.hand.clear()
            self.exhaust_pile.clear()
        elif message == Message.START_OF_TURN:
            # turn = data
            for effect in self.buffs + self.debuffs:
                if effect.subscribed is False:
                    effect.register(bus)
            ansiprint(f"<underline><bold>{self.name}</bold></underline>:")
            self.energy += self.energy_gain
            # INFO: Both Barricade and Calipers are not accounted for here and will be added later.
            self.block = 0
            self.draw_cards()
            self.plays_this_turn = 0
            ei.tick_effects(self)
            self.fresh_effects.clear()
        elif message == Message.END_OF_TURN:
            self.discard_pile += self.hand
            for card in self.hand:
                card.unsubscribe()
            sleep(1)
            view.clear()
        elif message == Message.ON_RELIC_ADD:
            relic, _ = data
            relic.register(bus)
        elif message == Message.ON_PLAYER_HEALTH_LOSS:
            # Check if we're dead
            enemy, player, damage = data
            if player.health <= 0:
                print(f"player.health: {player.health}")
                player.die()


class Enemy(Registerable):
    registers = [Message.START_OF_TURN, Message.END_OF_TURN, Message.ON_DEATH_OR_ESCAPE]
    player = None

    def __init__(self, health_range: list, block: int, name: str, powers: list[Effect] = None):
        self.uid = uuid4()
        if not powers:
            powers = []
        actual_health = random.randint(health_range[0], health_range[1])
        self.health = actual_health
        self.max_health = actual_health
        self.block = block
        self.name = name
        self.third_person_ref = (
            f"{self.name}'s"  # Python f-strings suck so I have to use this
        )
        self.past_moves = ["place"] * 3
        self.intent: str = ""
        self.next_move: list[tuple[str, str, tuple] | tuple[str, tuple]] = ""
        self.state = State.ALIVE
        self.buffs = powers
        self.debuffs = []
        self.stolen_gold = 0
        self.mode = ""
        self.flames = -1
        self.upgrade_burn = False
        self.active_turns = 1

    def __str__(self):
        return "Enemy"

    def __repr__(self):
        status = f"{self.name} (<red>{self.health} </red>/ <red>{self.max_health}</red> | <light-blue>{self.block} Block</light-blue>)"
        for effect in self.buffs + self.debuffs:
            status += " | " + effect.get_name()
        if self.flames > 0:
            status += f" | <yellow>{self.flames} Flames</yellow>"
        status += " | Intent: " + self.intent.replace('Σ', '')
        return status

    def set_intent(self):
        raise NotImplementedError("set_intent() must be implemented in a subclass")

    def execute_move(self, player: Player, enemies: list["Enemy"]):
        moves = 1
        display_name = "DEFAULT: UNKNOWN"
        for action in self.next_move:
            if moves == 1 and len(action) > 2:
                display_name, action, parameters = action
            else:
                action, parameters = action
            if action in ("Cowardly", "Sleeping", "Stunned") or action not in ("Attack", "Buff", "Debuff", "Status", "Block"):
                self.misc_move(enemies)
                sleep(1)
                view.clear()
                return
            ansiprint(f"<bold>{display_name}</bold>\n" if moves == 1 else "", end="")
            sleep(0.6)
            if action == "Attack":
                dmg = parameters[0]
                times = parameters[1] if len(parameters) > 1 else 1
                self.attack(dmg, times, target=player)
            elif action == "Buff":
                buff = parameters[0]
                amount = parameters[1] if len(parameters) > 1 else 1
                target = parameters[2] if len(parameters) > 2 else self
                ei.apply_effect(target=target, user=self, effect=buff, amount=amount)
            elif action == "Debuff":
                debuff = parameters[0]
                amount = parameters[1] if len(parameters) > 1 else 1
                target = parameters[2] if len(parameters) > 2 else player
                ei.apply_effect(target=target, user=self, effect=debuff, amount=amount)
            elif action == "Remove Effect":
                effect_name = parameters[0]
                effect_type = parameters[1]
                self.remove_effect(effect_name, effect_type)
            elif action == "Status":
                assert (len(parameters) >= 3), f"Status action requires 3 parameters: given {parameters}"
                status = parameters[0]
                amount = parameters[1]
                location = parameters[2].lower()
                self.status(status_card=status, amount=amount, location=location, player=player)
            elif action == "Block":
                block = parameters[0]
                target = parameters[1] if len(parameters) > 1 else None
                self.blocking(block, target)
            else:
                raise ValueError(f"Invalid action: {action}")
            sleep(0.2)
            moves += 1
        if display_name == "Inferno" and self.flames > -1:
            self.upgrade_burn = True
            self.flames = 0
        sleep(0.5)
        self.past_moves.append(display_name)
        self.active_turns += 1
        if self.flames > -1:
            self.flames += 1

    def misc_move(self, enemies):
        if len(self.next_move[0]) > 2:
            name, func_name, parameters = self.next_move[0]
        else:
            name, func_name = self.next_move[0]
        ansiprint(f"<bold>{name}</bold>")
        print(f"self.next_move: {self.next_move}")
        sleep(0.6)
        if func_name == "Cowardly":
            ansiprint("<italic>Hehe. Thanks for the money.<italic>")
            self.state = State.ESCAPED
            ansiprint(f"<italic><red>{self.name} has escaped</red></italic>")
        elif func_name == "Sleeping":
            sleeptalk = parameters[0]
            ansiprint(f"<italic>{sleeptalk}</italic>")
        elif func_name == "Stunned":
            ansiprint("<italic>Stunned!</italic>")
        elif func_name == "Summon":
            enemies = tuple(parameters[0])
            amount = int(parameters[1]) if len(parameters) > 1 else 1
            choice = bool(parameters[2]) if len(parameters) > 2 else False
            self.summon(enemies, amount, choice)
        elif func_name == "Explode":
            pass
        elif func_name == "Rebirth":
            for debuff in self.debuffs:
                if debuff not in ei.NON_STACKING_EFFECTS:
                    self.debuffs[debuff] = 0
                else:
                    self.debuffs[debuff] = False
            self.buffs["Curiosity"] = False
            self.buffs["Unawakened"] = False
        elif func_name == "Revive":
            self.health = math.floor(self.health * 0.5)
            ansiprint(f"<bold>{self.name}</bold> revived!")
        elif func_name == "Charging":
            message = parameters[0]
            ansiprint(f"{message}")
        elif func_name == "Split":
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
            for _ in range(2):
                enemies.append(split_into[self.name])
            ansiprint(f"{self.name} split into 2 {split_into[self.name].name}s")
        self.active_turns += 1

    def die(self):
        """
        Dies.
        """
        print(f"{self.name} has died.")
        self.state = State.DEAD
        for effect in self.buffs + self.debuffs:
            effect.unsubscribe()
        bus.publish(Message.ON_DEATH_OR_ESCAPE, (self))

    def debuff_and_buff_check(self):
        """
        Not finished
        """

    def move_spam_check(self, target_move, max_count) -> bool:
        """Returns False if the move occurs [max_count] times in a row. Otherwise returns True"""
        enough_moves = len(self.past_moves) >= max_count
        return not(enough_moves and all(move == target_move for move in self.past_moves[-max_count:]))

    def attack(self, dmg: int, times: int, target: Player):
        for _ in range(times):
            if target.state == State.DEAD:
                print(f"{self.name} halts attack: {target.name} is already dead.")
                return
            modifiable_dmg = Damage(dmg)
            bus.publish(Message.BEFORE_ATTACK, (self, target, modifiable_dmg))  # allows for damage modification
            dmg = modifiable_dmg.damage
            if dmg <= target.block:
                target.block -= dmg
                dmg = 0
                ansiprint("<light-blue>Blocked</light-blue>")
            elif dmg > target.block:
                dmg -= target.block
                dmg = max(0, dmg)
                ansiprint(f"{self.name} dealt {dmg}(<light-blue>{target.block} Blocked</light-blue>) damage to you.")
                target.block = 0
                target.health -= dmg
                bus.publish(Message.ON_PLAYER_HEALTH_LOSS, (self, target, dmg))
            bus.publish(Message.AFTER_ATTACK, (self, target, dmg))
        sleep(1)

    def remove_effect(self, effect_name, effect_type):
        if effect_name not in ei.ALL_EFFECTS:
            raise ValueError(f"{effect_name} is not a member of any debuff or buff list.")
        effect_types = {"Buffs": self.buffs, "Debuffs": self.debuffs}
        if effect_name not in ei.NON_STACKING_EFFECTS:
            effect_types[effect_type][effect_name] = 0
        else:
            effect_types[effect_type][effect_name] = False

    def blocking(self, block: int, target: "Enemy" = None, context: str=None):
        if not target:
            target = self
        target.block += block
        if context:
            ansiprint(f"{target.name} gained {block} <blue>Block</blue> from {context}")
        else:
            ansiprint(f"{target.name} gained {block} <blue>Block</blue>")
        sleep(1)

    def status(self, status_card: Card, amount: int, location: str, player: Player):
        locations = {
            "draw pile": player.draw_pile,
            "discard pile": player.discard_pile,
            "hand": player.hand,
        }
        pile = locations[location]
        assert isinstance(status_card, Card), f"status_card must be a Card. You passed {status_card} (type: {type(status_card)})."
        for _ in range(amount):
            upper_bound = len(location) - 1 if len(location) > 0 else 1
            insert_index = random.randint(0, upper_bound)
            pile.insert(insert_index, deepcopy(status_card))
        ansiprint(f"{player.name} gained {amount} {status_card.name} \nPlaced into {location}")
        sleep(1)

    def summon(self, enemy, amount: int, random_enemy: bool, enemies):
        if len(enemy) == 1:
            enemy = enemy[0]
        for _ in range(amount):
            chosen_enemy = random.choice(enemy) if random_enemy else enemy
            enemies.append(chosen_enemy)
            ansiprint(f"<bold>{chosen_enemy.name}</bold> summoned!")

    def callback(self, message, data):
        global bus
        if message == Message.START_OF_TURN:
            ansiprint(f"{self.name}'s current state: {self.state}")
            if self.state == State.ALIVE:
                for effect in self.buffs + self.debuffs:
                    if effect.subscribed is False:
                        effect.register(bus)
                ansiprint(f"<underline><bold>{self.name}</bold></underline>:")
                if "Block" not in self.intent:  # Checks the last move(its intent hasn't been updated yet) used to see if the enemy Blocked last turn
                    self.block = 0
                ei.tick_effects(self)
                print()
                bus.publish(Message.BEFORE_SET_INTENT, (self, bus))
                self.set_intent()
        elif message == Message.END_OF_TURN:
            player, enemies = data
            if self.state == State.ALIVE:
                self.execute_move(player, enemies)
            if self.health < 0:
                self.die()
            # Needs to be expanded at some point
        elif message == Message.ON_DEATH_OR_ESCAPE:
            dying_object = data
            self.handle_on_death_or_escape(dying_object)

    def handle_on_death_or_escape(self, dying_entity: Player|"Enemy"):
        if self.state == State.DEAD:
            return
        print(f"{self.name} observes the death of {dying_entity.name}.")


