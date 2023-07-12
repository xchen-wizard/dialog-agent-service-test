from __future__ import annotations

import logging
from datetime import datetime
from typing import List


logger = logging.getLogger()


class Turn:
    ts_fmt = '%Y-%m-%d %H:%M:%S'

    def __init__(self, rows: list):
        self.direction = rows[0].direction
        self.text = [(row.createdAt, row.body) for row in rows if row.body]
        self.session = [row.session for row in rows if row.session]

    def __str__(self):
        header = 'Wizard' if self.direction == 'outbound' else 'User'
        return ': '.join([header, self.formatted_text])

    @property
    def formatted_text(self):
        return '\n'.join([t[1] for t in self.text])

    def get_session(self):
        if self.session:
            if len(self.session) > 1:
                logger.warning(
                    f'got more than 1 session states for a turn: {self.session}')
            return self.session[0]  # either start or end
        else:
            return None

    def test_format(self, threshold_in_seconds=300):
        return ' '.join([t[1] for t in self.text if (self.text[-1][0] - t[0]).seconds < threshold_in_seconds])


class Conversation:
    def __init__(self, row_list: list, skip_opt_out=True):
        self.turns = []
        rows = []
        direction = None
        for row in row_list:
            if row.direction == direction:
                rows.append(row)
            else:
                if rows:
                    self.turns.append(Turn(rows))
                rows.clear()
                rows.append(row)
                direction = row.direction
        if rows:
            self.turns.append(Turn(rows))
        if skip_opt_out:
            self.turns = self.turns[2:]

    def __str__(self):
        return '\n'.join(map(str, self.turns))

    @property
    def n_turns(self):
        return len(self.turns)

    def format_train_test(self, threshold=300):
        for i, turn in enumerate(self.turns):
            if turn.direction == 'inbound':
                yield self.turns[i-1].test_format(), turn.test_format()
