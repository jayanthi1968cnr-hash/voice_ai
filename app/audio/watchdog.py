import logging, time

class DeviceWatchdog:
    def __init__(self, reinit_fn, cooldown=2.0, max_attempts=3):
        self.reinit_fn = reinit_fn
        self.cooldown = cooldown
        self.max_attempts = max_attempts

    def guard(self, fn, *args, **kwargs):
        attempts = 0
        while True:
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                attempts += 1
                logging.exception("Audio error; attempt %s/%s", attempts, self.max_attempts)
                if attempts >= self.max_attempts: raise
                time.sleep(self.cooldown)
                self.reinit_fn()
