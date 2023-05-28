import json
import math
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
import multiprocessing


STYLE = get_style_by_name('bw')
BACKROUND_COLOR = ImageColor.getrgb(STYLE.background_color)


def highlight_code(code, language, font_size=24):
    lexer = get_lexer_by_name(language)
    lexer.stripnl = False
    formatter = ImageFormatter(
        font_size=font_size,
        style=STYLE,
        line_number=True,
        line_number_chars=4,
        line_number_bg="#000000",
        line_number_fg='#ffffff',
    )
    return highlight(code, lexer, formatter)


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


def create_image(data, dimensions, final_font_size):
    # Add filepath and project name to the image
    text = f"({data['github_username']}::{data['project_name']}):{data['filepath']}"
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.8
    font_thickness = 2
    text_size, _ = cv2.getTextSize(text, font, font_scale, font_thickness)

    extended_content = data["content"] + "\n" * (data["max_lines"] - data["total_lines"])

    max_code_height = dimensions[1] - text_size[1]

    code_image = np.frombuffer(
        highlight_code(extended_content, data["language"], font_size=final_font_size),
        dtype=np.uint8,
    )
    code_image = cv2.imdecode(code_image, cv2.IMREAD_UNCHANGED)

    canvas_r = np.full((dimensions[1], dimensions[0]), dtype=np.uint8, fill_value=BACKROUND_COLOR[0])
    canvas_g = np.full((dimensions[1], dimensions[0]), dtype=np.uint8, fill_value=BACKROUND_COLOR[1])
    canvas_b = np.full((dimensions[1], dimensions[0]), dtype=np.uint8, fill_value=BACKROUND_COLOR[2])
    canvas = np.stack([canvas_r, canvas_g, canvas_b], axis=-1)
    code_image_slice = code_image
    code_image_width = code_image.shape[1]
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
        except Exception as e:
            logger.error(f"Unable to process file fully: {data['filepath']}")
            logger.error(e)
        i = i + 1
    cv2.putText(canvas, text, (0, text_size[1]), font, font_scale, (0, 0, 0), font_thickness)

    return canvas


def create_gif(config, gif_clip, change_files, gif_output_dir):
    frames = []
    logger.info(f"Processing gif for {gif_clip['name']}")
    gif_frames = int(config.get("gif_length", 5) / len(gif_clip["files"]) * config.get("gif_fps"))
    for change_file in change_files:
        img = create_image(change_file, gif_clip["dimensions"], change_file["font_size"][f"{gif_clip['name']}_gif"])
        frames.extend([img] * gif_frames)
    clip = ImageSequenceClip(frames, fps=config.get("gif_fps"))
    output_filename = f"{config.get('name')}_{gif_clip['name']}.gif"
    output_filepath = os.path.join(gif_output_dir, output_filename)
    clip.write_gif(output_filepath, fps=config.get("gif_fps"))


def create_gifs(config, change_files):
    gif_output_dir = os.path.expanduser(os.path.join(config.get("output_dir"), "gifs"))

    os.makedirs(gif_output_dir, exist_ok=True)

    gif_change_files = group_by_file(change_files)
    gif_clips = [
        {"name": resolution["name"], "dimensions": resolution["dimensions"], "files": gif_change_files}
        for resolution in config.get("gif_resolutions")
    ]

    processes = []
    for gif_clip in gif_clips:
        for gif_change_file_group in gif_clip["files"].values():
            p = multiprocessing.Process(
                target=create_gif,
                args=(config, gif_clip, gif_change_file_group, gif_output_dir),
            )
            processes.append(p)
            p.start()

    for p in processes:
        p.join()


def create_video(config, change_files):
    video_frames = int(config.get("video_length", 300) / len(change_files) * config.get("video_fps"))
    video_output_dir = os.path.expanduser(os.path.join(config.get("output_dir"), "videos"))

    os.makedirs(video_output_dir, exist_ok=True)

    video_clips = [
        {"name": video_resolution["name"], "dimensions": video_resolution["dimensions"], "frames": []}
        for video_resolution in config.get("video_resolutions")
    ]
    with multiprocessing.Pool() as pool:
        for clip_info in video_clips:
            starmap_args = [
                (change_file, clip_info["dimensions"], change_file["font_size"][f"{clip_info['name']}_video"])
                for change_file in change_files
            ]
            logger.info(f"Processing {clip_info['name']}_video")
            for img in pool.starmap(create_image, starmap_args):
                clip_info["frames"].extend([img] * video_frames)

    for clip_info in video_clips:
        clip = ImageSequenceClip(clip_info['frames'], fps=config.get("video_fps"))
        output_filename = f"{config.get('name')}_{clip_info['dimensions'][0]}x{clip_info['dimensions'][1]}.mp4"
        output_filepath = os.path.join(video_output_dir, output_filename)
        clip.write_videofile(output_filepath, fps=config.get("video_fps"))


def preprocess_change_files(change_files):
    # Remove empty files
    preprocessed_change_files = [change_file for change_file in change_files if change_file["content"] != ""]
    # Add number of lines per file
    preprocessed_change_files = [
        {**change_file, "total_lines": len(change_file["content"].split("\n"))}
        for change_file in preprocessed_change_files
    ]
    # Find the maximum number of lines per file, and the maximum number of characters per line per file
    max_lines = {
        filepath: 0 for filepath in set([change_file["filepath"] for change_file in preprocessed_change_files])
    }

    for change_file in preprocessed_change_files:
        max_lines[change_file["filepath"]] = max(max_lines[change_file["filepath"]], change_file["total_lines"])

    preprocessed_change_files = [
        {**change_file, "max_lines": max_lines[change_file["filepath"]], "font_size": {}}
        for change_file in preprocessed_change_files
    ]
    preprocessed_change_files = [
        change_file for change_file in preprocessed_change_files if change_file["max_lines"] > 0
    ]
    return preprocessed_change_files


def get_widest_files(change_files):
    max_line_chars = {filepath: 0 for filepath in set([change_file["filepath"] for change_file in change_files])}
    max_char_indexes = {}
    file_max_line_chars = 0
    for file_index, change_file in enumerate(change_files):
        for line in change_file["content"].split("\n"):
            file_max_line_chars = max(len(line), file_max_line_chars)
        if file_max_line_chars > max_line_chars[change_file["filepath"]]:
            max_line_chars[change_file["filepath"]] = file_max_line_chars
            max_char_indexes[change_file["filepath"]] = file_index
    return max_char_indexes


def get_font_size(change_file, resolution, type):
    text = f"({change_file['github_username']}::{change_file['project_name']}):{change_file['filepath']}"
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.8
    font_thickness = 2
    text_size, _ = cv2.getTextSize(text, font, font_scale, font_thickness)

    extended_content = change_file["content"] + "\n" * (change_file["max_lines"] - change_file["total_lines"])

    logger.info(f"Determining font size for: {change_file['filepath']} for {resolution['name']} {type}")
    max_code_height = resolution["dimensions"][1] - text_size[1]
    high = 400
    low = 1
    precision = 0.1
    font_size = (high + low) / 2
    while high - low > precision:
        font_size = (high + low) / 2
        logger.debug(f"{change_file['filepath']} > font_size: {font_size}")
        code_image = np.frombuffer(
            highlight_code(extended_content, change_file["language"], font_size=font_size), dtype=np.uint8
        )
        code_image = cv2.imdecode(code_image, cv2.IMREAD_UNCHANGED)
        code_image_width = code_image.shape[1]
        code_image_height = code_image.shape[0]
        wrap_count = math.ceil(code_image_height / max_code_height)
        wrap_width = wrap_count * code_image_width

        if wrap_width > resolution["dimensions"][0]:
            high = font_size
        else:
            low = font_size  # increase the font size
    return (change_file['filepath'], f"{resolution['name']}_{type}", font_size)


def get_change_files(config):
    changes_dir = os.path.expanduser(os.path.join(config.get("output_dir"), "changes"))
    change_filenames = sorted(glob.glob(os.path.join(changes_dir, f"*")))
    change_files = [json.load(open(change_filename, "r")) for change_filename in change_filenames]

    change_files = preprocess_change_files(change_files)
    max_char_indexes = get_widest_files(change_files)

    font_sizes = {}

    starmap_args = []
    with multiprocessing.Pool() as pool:
        for _, max_char_index in max_char_indexes.items():
            change_file = change_files[max_char_index]
            if config.get("video"):
                starmap_args.extend(
                    [(change_file, resolution, "video") for resolution in config.get("video_resolutions")]
                )
            if config.get("gifs"):
                starmap_args.extend([(change_file, resolution, "gif") for resolution in config.get("gif_resolutions")])

        for filepath, resolution_key, font_size in pool.starmap(get_font_size, starmap_args):
            font_sizes.setdefault(filepath, {})[resolution_key] = font_size

    change_files = [{**change_file, "font_size": font_sizes[change_file['filepath']]} for change_file in change_files]

    if change_files:
        return change_files
    else:
        return None


def create_media():
    project_dir = os.path.expanduser(input("Enter the path to the project directory: "))
    config_filepath = os.path.join(project_dir, "tracer.json")
    config = Config(config_filepath)

    change_files = get_change_files(config)

    if config.get("group_by_file", True):
        change_files = group_by_file(change_files, flatten=True)

    if config.get("video", False):
        create_video(config, change_files)

    if config.get("gifs", False):
        create_gifs(config, change_files)


if __name__ == "__main__":
    create_media()
