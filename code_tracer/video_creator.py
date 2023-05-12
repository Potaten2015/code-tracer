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
from PIL import ImageColor
from itertools import groupby

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

FPS = 60
STYLE = get_style_by_name('bw')
BACKROUND_COLOR = ImageColor.getrgb(STYLE.background_color)


def get_language(filepath):
    file_extension = os.path.splitext(filepath)[-1]
    return SUPPORTED_LANGUAGES.get(file_extension, "text")


def highlight_code(code, language, font_size=24):
    lexer = get_lexer_by_name(language)
    formatter = ImageFormatter(
        font_size=font_size,
        style=STYLE,
        line_number=True,
        line_number_chars=4,
        line_number_bg="#000000",
        line_number_fg='#ffffff',
    )
    return highlight(code, lexer, formatter)


def create_image(data, dimensions):
    # Add filepath and project name to the image
    text = f"""({data['github_username']}
    {data['project_name']})
    {data['filepath']}"""
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.8
    font_thickness = 2
    text_size, _ = cv2.getTextSize(text, font, font_scale, font_thickness)

    extended_content = data["content"] + "\n" * (data["max_lines"] - data["total_lines"])

    too_big = True
    too_small = True
    max_code_height = dimensions[1] - text_size[1]
    font_size = 24

    while too_big:
        code_image = np.frombuffer(
            highlight_code(extended_content, data["language"], font_size=font_size), dtype=np.uint8
        )
        code_image = cv2.imdecode(code_image, cv2.IMREAD_UNCHANGED)
        code_image_width = code_image.shape[1]
        code_image_height = code_image.shape[0]

    canvas_r = np.full((dimensions[1], dimensions[0]), dtype=np.uint8, fill_value=BACKROUND_COLOR[0])
    canvas_g = np.full((dimensions[1], dimensions[0]), dtype=np.uint8, fill_value=BACKROUND_COLOR[1])
    canvas_b = np.full((dimensions[1], dimensions[0]), dtype=np.uint8, fill_value=BACKROUND_COLOR[2])
    canvas = np.stack([canvas_r, canvas_g, canvas_b], axis=-1)
    code_image_slice = code_image
    i = 0
    while code_image_slice.size != 0:
        code_image_slice = code_image[i * max_code_height : (i + 1) * max_code_height, :, :]
        if code_image_slice.size == 0:
            break
        if code_image_slice.shape[1] + (i * code_image_width) > dimensions[0]:
            code_image_slice = code_image_slice[:, : dimensions[0] - (i * code_image_width), :]
        try:
            canvas[
                text_size[1] : code_image_slice.shape[0] + text_size[1],
                i * code_image_width : i * code_image_width + code_image_slice.shape[1],
                :,
            ] = code_image_slice
        except:
            print("error")
        i = i + 1
    cv2.putText(canvas, text, (0, text_size[1]), font, font_scale, (0, 0, 0), font_thickness)

    return canvas


def create_video(config):
    output_folder = os.path.join(config.get("output_folder"), config.get("name"))
    changes_dir = os.path.join(output_folder, "changes")
    change_files = get_change_files(changes_dir, group_by_file=config.get("group_by_file", False))
    output_dir = os.path.join(output_folder, "videos")
    clip_frames = int(config.get("video_length", 300) / len(change_files) * FPS)

    os.makedirs(output_dir, exist_ok=True)

    if config.get("group_by_file", True):
        change_files = group_by_file(change_files, flatten=True)

    clips = [
        {"name": resolution["name"], "dimensions": resolution["dimensions"], "frames": []}
        for resolution in config.get("resolutions")
    ]

    if config.get("gifs", True):
        gif_clips = group_by_file(change_files)
        gif_clips = [
            {
                "name": filepath,
                "dimensions": (config.get("gif_width", 500), config.get("gif_height", 500)),
                "frames": [],
            }
            for filepath, change_file in gif_clips.items()
        ]
        for gif_clip in gif_clips:
            ## TODO: Create gifs
            pass

    for change_file in change_files:
        for (
            i,
            clip_info,
        ) in enumerate(clips):
            logger.info(f"Processing {change_file['filepath']} for {clip_info['name']}")
            img = create_image(change_file, clip_info["dimensions"])
            clips[i]["frames"].extend([img] * clip_frames)

    for clip_info in clips:
        clip = ImageSequenceClip(clip_info['frames'], fps=FPS)
        output_filename = f"{config.get('name')}_{clip_info['dimensions'][0]}x{clip_info['dimensions'][1]}.mp4"
        output_filepath = os.path.join(output_dir, output_filename)
        clip.write_videofile(output_filepath, fps=FPS)


def group_by_file(changes_files, flatten=False):
    grouped_changes = {}
    for change_file in changes_files:
        if change_file["filepath"] in grouped_changes:
            grouped_changes[change_file["filepath"]].append(change_file)
        else:
            grouped_changes[change_file["filepath"]] = [change_file]

    if flatten:
        new_changes_files = []
        for _, changes in grouped_changes.items():
            new_changes_files.extend(changes)
        return new_changes_files

    return grouped_changes


if __name__ == "__main__":
    project_dir = input("Enter the path to the project directory: ")
    config_filepath = os.path.join(project_dir, "tracer.json")
    config = Config(config_filepath)
    create_video(project_dir, config)


def get_change_files(changes_dir):
    change_filenames = sorted(glob.glob(os.path.join(changes_dir, f"*")))
    change_files = [json.load(open(change_filename, "r")) for change_filename in change_filenames]
    change_files = [
        {**change_file, "total_lines": len(change_file["content"].split("\n"))} for change_file in change_files
    ]
    max_lines = {filepath: 0 for filepath in set([change_file["filepath"] for change_file in change_files])}
    for change_file in change_files:
        max_lines[change_file["filepath"]] = max(max_lines[change_file["filepath"]], change_file["total_lines"])
    change_files = [{**change_file, "max_lines": max_lines[change_file["filepath"]]} for change_file in change_files]

    if change_files:
        return change_files
    else:
        return None
