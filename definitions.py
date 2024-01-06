'''
This file contains the definitions of various Enums.
'''

from enum import StrEnum

class Topic(StrEnum):
    '''These represent the types of messages that can be sent to the message bus.'''
    START_OF_COMBAT = 'start_of_combat'
    START_OF_TURN = 'start_of_turn'
    END_OF_TURN = 'end_of_turn'
    BEFORE_ATTACK = 'before_attack'
    AFTER_ATTACK = 'after_attack'

