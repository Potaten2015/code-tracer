import logging
import json

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging

TIME_FORMAT = '%Y.%m.%d-%H:%M:%S'


class Config:
    def __init__(self, filepath) -> None:
        self.load(filepath)

    def load(self, filepath):
        logger.info(f"Loading config from {filepath}")
        with open(filepath, 'r') as f:
            self.config = json.load(f)

    def get(self, key, default=None):
        result = self.config.get(key)
        if result:
            return result
        elif default:
            return default
        else:
            raise KeyError(f"Key {key} not found in config and no default provided")

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
