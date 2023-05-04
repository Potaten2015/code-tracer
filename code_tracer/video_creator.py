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

VIDEO_VARIATIONS = [("vertical", (2160, 3840)), ("horizontal", (3840, 2160))]


def get_language(filename):
    file_extension = os.path.splitext(filename)[-1]
    return SUPPORTED_LANGUAGES.get(file_extension, "text")


def highlight_code(code, language):
    lexer = get_lexer_by_name(language)
    formatter = ImageFormatter(font_size=24)
    return highlight(code, lexer, formatter)


def create_image(data, aspect_ratio):
    code_image = np.frombuffer(highlight_code(data["content"], data["language"]), dtype=np.uint8)
    code_image = cv2.imdecode(code_image, cv2.IMREAD_UNCHANGED)

    # Add filename and project name to the image
    text = f"{data['filename']} ({data['project_name']})"
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
    cv2.putText(canvas, text, (0, text_size[1]), font, font_scale, (255, 255, 255), font_thickness)

    return canvas


def create_video(config):
    output_folder = os.path.join(config["output_folder"], config["name"])
    changes_dir = os.path.join(output_folder, "changes")
    output_dir = os.path.join(output_folder, "videos")
    os.makedirs(output_dir, exist_ok=True)

    clips = [{"name": name, "aspect_ratio": aspect_ratio, "frames": []} for name, aspect_ratio in VIDEO_VARIATIONS]
    for change_filename in sorted(os.listdir(changes_dir)):
        change_filepath = os.path.join(changes_dir, change_filename)
        with open(change_filepath, "r") as f:
            data = json.load(f)

        for (
            i,
            clip_info,
        ) in enumerate(clips):
            img = create_image(data, clip_info["aspect_ratio"])
            clips[i]["frames"].append(img)

    max_video_length = config["max_video_length"]
    for clip_info in clips:
        clip = ImageSequenceClip(clip_info['frames'], fps=60)
        if clip.duration > max_video_length:
            clip = clip.subclip(0, max_video_length)
        output_filename = f"{config['name']}_{clip_info['aspect_ratio'][0]}x{clip_info['aspect_ratio'][1]}.mp4"
        output_filepath = os.path.join(output_dir, output_filename)
        clip.write_videofile(output_filepath, fps=60)


if __name__ == "__main__":
    project_dir = input("Enter the path to the project directory: ")
    max_video_length_default = 300
    max_video_length = (
        input(f"Enter maximum video length (default: {max_video_length_default}s)") or max_video_length_default
    )
    config_filepath = os.path.join(project_dir, "config.json")
    with open(config_filepath, "r") as f:
        config = json.load(f)
    config["max_video_length"] = int(max_video_length)
    create_video(project_dir, config)
