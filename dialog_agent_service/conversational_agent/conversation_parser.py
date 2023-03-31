from __future__ import annotations

from typing import List
from typing import Tuple


class Turn:

    def __init__(self, direction, text: list):
        self.direction = direction
        self.text = text

    def __str__(self):
        header = 'Seller' if self.direction == 'outbound' else 'Buyer'
        return ': '.join([header, self.formatted_text])

    @property
    def formatted_text(self):
        return '\n'.join(self.text)


class Conversation:
    def __init__(self, docs: list[tuple[str, str]], skip_opt_out=False):
        """
        Args:
            docs:
            skip_opt_out: default to false. ToDo: We cannot assume the first two messages are opt in messages
        """
        self.turns = []
        text = []
        last_direction = None
        for direction, body in docs:
            if direction == last_direction:
                text.append(body)
            else:
                if text:
                    self.turns.append(Turn(last_direction, text))
                text = []   # initialize a new list obj instead of clear the original
                text.append(body)
                last_direction = direction
        if text:
            self.turns.append(Turn(last_direction, text))
        if skip_opt_out:
            self.turns = self.turns[2:]

    def __str__(self):
        return '\n'.join(map(str, self.turns))

    @property
    def n_turns(self):
        return len(self.turns)
