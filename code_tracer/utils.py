import logging
import json
from constants import DEFAULTS

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


class Config:
    def __init__(self, filepath) -> None:
        self.filepath = filepath
        self.load(self.filepath)
        self._add_defaults()

    def _add_defaults(self):
        complete = True
        for key, value in DEFAULTS.items():
            if key not in self.config:
                complete = False
                logger.info(f"Key {key} not found in config, using default value {value}")
                self.config[key] = value
        if not complete:
            self.write(self.filepath)

    def load(self, filepath):
        logger.info(f"Loading config from {filepath}")
        with open(filepath, 'r') as f:
            self.config = json.load(f)
        self._add_defaults()
        if self.config.get("log_level"):
            logger.setLevel(self.config.get("log_level").upper())

    def get(self, key, default=None):
        result = self.config.get(key)
        if result is not None:
            return result
        elif default:
            return default
        else:
            raise KeyError(f"Key '{key}' not found in config and no default provided")

    def write(self, filepath):
        logger.info(f"Writing config to {filepath}")
        with open(filepath, 'w') as f:
            json.dump(self.config, f, indent=4)

    def append(self, key, value):
        try:
            self.config[key].append(value)
        except KeyError:
            self.config[key] = [value]

    def set(self, key, value):
        self.config[key] = value

    def check_errors(self):
        pass
