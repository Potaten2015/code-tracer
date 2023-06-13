import logging
import json
from constants import DEFAULTS

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()
logger.setLevel(logging.CRITICAL)


class Config:
    def __init__(self, filepath) -> None:
        self.filepath = filepath
        self.load(self.filepath)
        self._add_defaults()
        self.local_config = {}

    def _add_defaults(self):
        for key, value in DEFAULTS.items():
            if key not in self.config:
                logger.info(f"Key {key} not found in config, using default value {value}")
                self.config[key] = value
        self.config["render_sessions"] = list(set(self.config["render_sessions"]))
        self.config["all_sessions"] = list(set(self.config["all_sessions"]))
        self.config["render_sessions"].sort()
        self.write(self.filepath)
        self.config["session_folder"] = "_".join(self.config["render_sessions"])

    def load(self, filepath):
        logger.info(f"Loading config from {filepath}")
        with open(filepath, 'r') as f:
            self.config = json.load(f)
        self._add_defaults()
        self.logger = logger
        self.logger.setLevel(self.config.get("log_level").upper())

    def get(self, key, default=None):
        combined_config = {**self.config, **self.local_config}
        result = combined_config.get(key)
        if result is not None:
            return result
        elif default:
            return default
        else:
            raise KeyError(f"Key '{key}' not found in config and no default provided")

    def write(self, filepath=None):
        filepath = filepath or self.filepath
        logger.info(f"Writing config to {filepath}")
        with open(filepath, 'w') as f:
            json.dump(self.config, f, indent=4)

    def append(self, key, value, local=False):
        if local:
            self.local_config.setdefault(key, []).append(value)
        else:
            self.config.setdefault(key, []).append(value)

    def set(self, key, value, local=False):
        if local:
            self.local_config[key] = value
        else:
            self.config[key] = value

    def check_errors(self):
        pass
