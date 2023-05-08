import json
import os
import cv2
import numpy as np
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import ImageFormatter
from pygments.styles import get_style_by_name
from moviepy.editor import ImageSequenceClip
from utils import Config, logger
import glob

SUPPORTED_LANGUAGES = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".json": "json",
    ".md": "markdown",
    ".html": "html",
    # Add more language mappings here
}

VIDEO_VARIATIONS = [("vertical", (2160, 3840)), ("horizontal", (3840, 2160))]
FPS = 60


def get_language(filename):
    file_extension = os.path.splitext(filename)[-1]
    return SUPPORTED_LANGUAGES.get(file_extension, "text")


def highlight_code(code, language):
    lexer = get_lexer_by_name(language)
    style = get_style_by_name('rrt')
    formatter = ImageFormatter(font_size=24, style=style)
    return highlight(code, lexer, formatter)


def create_image(data, aspect_ratio):
    code_image = np.frombuffer(highlight_code(data["content"], data["language"]), dtype=np.uint8)
    code_image = cv2.imdecode(code_image, cv2.IMREAD_UNCHANGED)

    # Add filename and project name to the image
    text = f"({data['github_username']}\n{data['project_name']})\n{data['filepath']}\n"
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.8
    font_thickness = 2
    text_size, _ = cv2.getTextSize(text, font, font_scale, font_thickness)
    canvas = np.zeros((aspect_ratio[0], aspect_ratio[1], 3), dtype=np.uint8)
    if code_image.shape[0] > aspect_ratio[0] - text_size[1]:
        code_image = code_image[: aspect_ratio[0] - text_size[1], :, :]
    if code_image.shape[1] > aspect_ratio[1]:
        code_image = code_image[:, : aspect_ratio[1], :]
    canvas[text_size[1] : text_size[1] + code_image.shape[0], : code_image.shape[1], :] = code_image
    cv2.putText(canvas, text, (0, text_size[1]), font, font_scale, (0, 0, 0), font_thickness)

    return canvas


def create_video(config):
    output_folder = os.path.join(config.get("output_folder"), config.get("name"))
    changes_dir = os.path.join(output_folder, "changes")
    change_files = get_change_files(changes_dir)
    output_dir = os.path.join(output_folder, "videos")
    clip_frames = int(config.get("video_length", 300) / len(change_files) * FPS)

    os.makedirs(output_dir, exist_ok=True)

    clips = [{"name": name, "aspect_ratio": aspect_ratio, "frames": []} for name, aspect_ratio in VIDEO_VARIATIONS]
    for change_file in change_files:
        for (
            i,
            clip_info,
        ) in enumerate(clips):
            logger.info(f"Processing {change_file['filepath']} for {clip_info['name']}")
            img = create_image(change_file, clip_info["aspect_ratio"])
            clips[i]["frames"].extend([img] * clip_frames)

    for clip_info in clips:
        clip = ImageSequenceClip(clip_info['frames'], fps=FPS)
        output_filename = f"{config.get('name')}_{clip_info['aspect_ratio'][0]}x{clip_info['aspect_ratio'][1]}.mp4"
        output_filepath = os.path.join(output_dir, output_filename)
        clip.write_videofile(output_filepath, fps=FPS)


if __name__ == "__main__":
    project_dir = input("Enter the path to the project directory: ")
    config_filepath = os.path.join(project_dir, "config.json")
    config = Config(config_filepath)
    create_video(project_dir, config)


def get_change_files(changes_dir):
    change_filenames = sorted(glob.glob(os.path.join(changes_dir, f"*")))
    change_files = [json.load(open(change_filename, "r")) for change_filename in change_filenames]
    if change_files:
        return change_files
    else:
        return None
