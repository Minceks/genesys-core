"""Benchmark-only, persistent reservation guard at the paid API boundary."""
import json
from decimal import Decimal
from pathlib import Path
from threading import Lock


class SpendLimit(RuntimeError):
    pass


class SpendGuard:
    # Verified at https://developers.openai.com/api/docs/models/gpt-5-mini
    # Reserve the full model context, not an optimistic text-token estimate.
    MODEL = 'gpt-5-mini'
    INPUT = Decimal('0.25') / 1000000
    OUTPUT = Decimal('2') / 1000000
    CONTEXT = 400000

    def __init__(self, path, limit):
        self.path, self.limit, self.lock = Path(path), Decimal(str(limit)), Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.save({'limitUsd': str(self.limit), 'chargedUpperUsd': '0', 'calls': []})
        if Decimal(self.read()['limitUsd']) != self.limit:
            raise ValueError('Cannot change the limit of an existing benchmark ledger')

    def read(self):
        return json.loads(self.path.read_text(encoding='utf-8'))

    def save(self, data):
        temporary = self.path.with_suffix('.next')
        temporary.write_text(json.dumps(data, indent=2), encoding='utf-8')
        temporary.replace(self.path)

    def call(self, create, **options):
        if options.get('model') != self.MODEL:
            raise SpendLimit('Unpriced model rejected before API call')
        output = options.get('max_completion_tokens')
        if not isinstance(output, int) or not 1 <= output <= 24000:
            raise SpendLimit('A bounded output allowance is required')
        reservation = self.CONTEXT * self.INPUT + output * self.OUTPUT
        with self.lock:
            ledger = self.read()
            if Decimal(ledger['chargedUpperUsd']) + reservation > self.limit:
                raise SpendLimit('Benchmark model spending ceiling reached; no API call was made')
            index = len(ledger['calls'])
            ledger['chargedUpperUsd'] = str(Decimal(ledger['chargedUpperUsd']) + reservation)
            ledger['calls'].append({'reservedUsd': str(reservation), 'state': 'reserved'})
            self.save(ledger)
        # Exceptions retain the complete reservation, including timeouts whose
        # billable provider usage is unknown. The SDK must have retries disabled.
        response = create(**options)
        usage = getattr(response, 'usage', None)
        incoming, outgoing = getattr(usage, 'prompt_tokens', None), getattr(usage, 'completion_tokens', None)
        if (isinstance(incoming, int) and isinstance(outgoing, int)
                and 0 <= incoming <= self.CONTEXT and 0 <= outgoing <= output):
            cost = incoming * self.INPUT + outgoing * self.OUTPUT
            with self.lock:
                ledger = self.read()
                ledger['chargedUpperUsd'] = str(Decimal(ledger['chargedUpperUsd']) - reservation + cost)
                ledger['calls'][index].update(state='reported', inputTokens=incoming,
                    outputTokens=outgoing, upperUsd=str(cost))
                self.save(ledger)
        return response
