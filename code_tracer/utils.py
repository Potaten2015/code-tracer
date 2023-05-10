import logging
import json

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging

TIME_FORMAT = '%Y.%m.%d-%H:%M:%S'
DEFAULTS = {
    "ignore": [
        "*node_modules*",
        "*venv*",
        "*__pycache__*",
    ],
    "interval": 5,
    "video_length": 60,
    "gifs": False,
    "group_by_file": False,
    "video": True,
    "resolutions": {
        {"name": "landscape", "dimensions": [4096, 2160]},
        {"name": "portrait", "dimensions": [2160, 4096]},
    },
    "gif_width": 500,
    "gif_height": 500,
}


class Config:
    def __init__(self, filepath) -> None:
        self.load(filepath)

    def load(self, filepath):
        logger.info(f"Loading config from {filepath}")
        with open(filepath, 'r') as f:
            self.config = json.load(f)
        complete = True
        for key, value in DEFAULTS.items():
            if key not in self.config:
                complete = False
                logger.info(f"Key {key} not found in config, using default value {value}")
                self.config[key] = value
        if not complete:
            self.write(filepath)

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

    def check_errors(self):
        pass
