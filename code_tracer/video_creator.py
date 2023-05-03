import json
import os
import cv2
import numpy as np
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import ImageFormatter
from moviepy.editor import ImageSequenceClip

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


def get_language(filename):
    file_extension = os.path.splitext(filename)[-1]
    return SUPPORTED_LANGUAGES.get(file_extension, "text")


def highlight_code(code, language):
    lexer = get_lexer_by_name(language)
    formatter = ImageFormatter(font_size=24)
    return highlight(code, lexer, formatter)


def create_image(data):
    code_image = np.frombuffer(highlight_code(data["content"], data["language"]), dtype=np.uint8)
    code_image = cv2.imdecode(code_image, cv2.IMREAD_UNCHANGED)

    # Add filename and project name to the image
    text = f"{data['filename']} ({data['project_name']})"
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.8
    font_thickness = 2
    text_size, _ = cv2.getTextSize(text, font, font_scale, font_thickness)
    img_height, img_width = code_image.shape[:2]
    padding = 20
    canvas = np.zeros((img_height + text_size[1] + padding, img_width, 3), dtype=np.uint8)
    canvas[text_size[1] :, :, :] = code_image
    cv2.putText(canvas, text, (0, text_size[1]), font, font_scale, (255, 255, 255), font_thickness)

    return canvas


def create_video(config):
    output_folder = os.path.join(config["output_folder"], config["name"])
    changes_dir = os.path.join(output_folder, "changes")
    output_dir = os.path.join(output_folder, "videos")
    os.makedirs(output_dir, exist_ok=True)

    images = []
    for change_filename in sorted(os.listdir(changes_dir)):
        change_filepath = os.path.join(changes_dir, change_filename)
        with open(change_filepath, "r") as f:
            data = json.load(f)

        img = create_image(data)
        images.append(img)

    clip = ImageSequenceClip(images, fps=60)
    max_video_length = config["max_video_length"]

    if clip.duration > max_video_length:
        clip = clip.subclip(0, max_video_length)

    for aspect_ratio, size in [("vertical", (2160, 3840)), ("horizontal", (3840, 2160))]:
        resized_clip = clip.resize(size)
        output_filename = f"{config['name']}_{aspect_ratio}.mp4"
        output_filepath = os.path.join(output_dir, output_filename)
        resized_clip.write_videofile(output_filepath, fps=60)


if __name__ == "__main__":
    project_dir = input("Enter the path to the project directory: ")
    config_filepath = os.path.join(project_dir, "config.json")
    with open(config_filepath, "r") as f:
        config = json.load(f)

    create_video(project_dir, config)
