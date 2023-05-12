TIME_FORMAT = '%Y.%m.%d-%H:%M:%S'
DEFAULTS = {
    "ignore": [
        "*node_modules*",
        "*venv*",
        "*__pycache__*",
    ],
    "interval": 1,
    "video_length": 60,
    "gifs": False,
    "gif_width": 500,
    "gif_height": 500,
    "gif_length": 10,
    "gif_fps": 10,
    "group_by_file": False,
    "video": True,
    "video_fps": 60,
    "resolutions": [
        {"name": "landscape", "dimensions": [4096, 2160]},
        {"name": "portrait", "dimensions": [2160, 4096]},
    ],
    "log_level": "INFO",
}
