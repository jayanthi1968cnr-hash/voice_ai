class EndpointPolicy:
    def __init__(self, base_tail_ms=1200, max_tail_ms=2800, energy_floor=0.015):
        self.base = base_tail_ms
        self.max = max_tail_ms
        self.energy = energy_floor

    def next_timeout(self, recent_energy, is_short_utterance):
        if recent_energy < self.energy:
            return self.base
        return self.max if not is_short_utterance else int(self.base * 0.8)
