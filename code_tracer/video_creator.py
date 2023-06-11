import cv2
import glob
import json
import math
import multiprocessing
import numpy as np
import os
from tqdm import tqdm

from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import ImageFormatter
from pygments.styles import get_style_by_name
from moviepy.editor import ImageSequenceClip
from PIL import ImageColor

from utils import Config, logger


STYLE = get_style_by_name('bw')
BACKROUND_COLOR = ImageColor.getrgb(STYLE.background_color)
HEADER_FONT = cv2.FONT_HERSHEY_SIMPLEX
HEADER_FONT_SCALE = 0.8
HEADER_FONT_THICKNESS = 2


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


def add_header(change_file, canvas=None):
    text = f"{change_file['github_username']}::{change_file['project_name']}::{change_file['filepath']}"
    header_size, _ = cv2.getTextSize(text, HEADER_FONT, HEADER_FONT_SCALE, HEADER_FONT_THICKNESS)
    if canvas is not None:
        cv2.putText(canvas, text, (0, header_size[1]), HEADER_FONT, HEADER_FONT_SCALE, (0, 0, 0), HEADER_FONT_THICKNESS)
    return header_size


def add_filler_lines(change_file):
    return change_file["content"] + ("\n" * (change_file["max_lines"] - change_file["total_lines"]))


def create_canvas(change_file, dimensions):
    canvas_r = np.full((dimensions[1], dimensions[0]), dtype=np.uint8, fill_value=BACKROUND_COLOR[0])
    canvas_g = np.full((dimensions[1], dimensions[0]), dtype=np.uint8, fill_value=BACKROUND_COLOR[1])
    canvas_b = np.full((dimensions[1], dimensions[0]), dtype=np.uint8, fill_value=BACKROUND_COLOR[2])
    canvas = np.stack([canvas_r, canvas_g, canvas_b], axis=-1)
    return canvas


def create_image(change_file, dimensions, final_font_size):
    canvas = create_canvas(change_file, dimensions)
    header_size = add_header(change_file, canvas=canvas)
    extended_content = add_filler_lines(change_file)
    max_code_height = dimensions[1] - header_size[1]

    code_image = np.frombuffer(
        highlight_code(extended_content, change_file["language"], font_size=final_font_size),
        dtype=np.uint8,
    )
    code_image = cv2.imdecode(code_image, cv2.IMREAD_UNCHANGED)

    code_image_slice = code_image
    code_image_width = code_image.shape[1]

    i = 0
    slice = 0
    while code_image_slice.size != 0:
        slice = slice + 1
        code_image_slice = code_image[i * max_code_height : (i + 1) * max_code_height, :, :]
        if code_image_slice.size == 0:
            break
        if code_image_slice.shape[0] > max_code_height:
            code_image_slice = code_image_slice[:max_code_height, :, :]
        if code_image_slice.shape[1] > dimensions[0]:
            code_image_slice = code_image_slice[:, : dimensions[0], :]
        try:
            canvas[
                header_size[1] : code_image_slice.shape[0] + header_size[1],
                i * code_image_width : i * code_image_width + code_image_slice.shape[1],
                :,
            ] = code_image_slice
        except Exception as e:
            logger.error(
                f"Unable to process file fully: {change_file['filepath']} - slice: {slice} - code_image_slice.shape:"
                f" {code_image_slice.shape} - canvas.shape: {canvas.shape}"
            )
            logger.error(e)
        i = i + 1

    return canvas


def create_gif(config, gif_clip, change_files, gif_output_dir):
    frames = []
    logger.info(f"Processing gif for {gif_clip['name']}")
    gif_frames = int(config.get("gif_length", 5) / len(gif_clip["files"]) * config.get("gif_fps"))
    for change_file in change_files:
        img = create_image(change_file, gif_clip["dimensions"], change_file["font_size"][f"{gif_clip['name']}_gif"])
        frames.extend([img] * gif_frames)
    if frames:
        clip = ImageSequenceClip(frames, fps=config.get("gif_fps"))
        output_filename = f"{config.get('name')}_{gif_clip['name']}_{change_files[0]['filepath']}.gif"
        output_filepath = os.path.join(gif_output_dir, output_filename)
        clip.write_gif(output_filepath, fps=config.get("gif_fps"))


def create_gifs(config, change_files):
    gif_output_dir = os.path.expanduser(os.path.join(config.get("output_dir"), "gifs", config.get("session_folder")))

    os.makedirs(gif_output_dir, exist_ok=True)

    gif_change_files = group_by_file(change_files)
    gif_clips = [
        {"name": resolution["name"], "dimensions": resolution["dimensions"], "files": gif_change_files}
        for resolution in config.get("gif_resolutions")
    ]

    processes = []
    logger.info("Creating gifs...")
    for gif_clip in gif_clips:
        logger.info(f"Processing {gif_clip['name']}")
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
    video_output_dir = os.path.expanduser(
        os.path.join(config.get("output_dir"), "videos", config.get("session_folder"))
    )

    os.makedirs(video_output_dir, exist_ok=True)

    video_clips = [
        {"name": video_resolution["name"], "dimensions": video_resolution["dimensions"], "frames": []}
        for video_resolution in config.get("video_resolutions")
    ]
    logger.info("Creating frames...")
    with multiprocessing.Pool(processes=None if config.get("multi_processing") else 1) as pool:
        for clip_info in video_clips:
            starmap_args = [
                (change_file, clip_info["dimensions"], change_file["font_size"][f"{clip_info['name']}_video"])
                for change_file in change_files
            ]
            logger.info(f"Processing {clip_info['name']}_video")
            for img in tqdm(pool.starmap(create_image, starmap_args), total=len(starmap_args)):
                clip_info["frames"].extend([img] * video_frames)

    logger.info("Creating videos...")
    for clip_info in video_clips:
        logger.info(f"clips: {len(clip_info['frames'])} - {clip_info['name']}_video")
        if clip_info["frames"]:
            clip = ImageSequenceClip(clip_info['frames'], fps=config.get("video_fps"))
            output_filename = f"{config.get('name')}_{clip_info['dimensions'][0]}x{clip_info['dimensions'][1]}.mp4"
            output_filepath = os.path.join(video_output_dir, output_filename)
            clip.write_videofile(output_filepath, fps=config.get("video_fps"))


def preprocess_change_files(config, change_files):
    preprocessed_change_files = [change_file for change_file in change_files if change_file["content"] != ""]
    if not preprocessed_change_files:
        logger.error("All change files are empty.")
        exit(1)
    for change_file in preprocessed_change_files:
        if not change_file.get("session"):
            change_file["session"] = "default"
    preprocessed_change_files = [
        change_file
        for change_file in preprocessed_change_files
        if change_file.get("session") in config.get("render_sessions")
    ]
    if not preprocessed_change_files:
        logger.error(f"No change files found for the specified render sessions: {config.get('render_sessions')} .")
        exit(1)
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
    max_widths = {filepath: 0 for filepath in set([change_file["filepath"] for change_file in change_files])}
    max_width_indices = {}
    logger.info("Determining widest change file per file path...")
    for file_index, change_file in tqdm(enumerate(change_files), total=len(change_files)):
        extended_content = add_filler_lines(change_file)
        code_image = np.frombuffer(
            highlight_code(extended_content, change_file["language"], font_size=1), dtype=np.uint8
        )
        code_image = cv2.imdecode(code_image, cv2.IMREAD_UNCHANGED)
        if code_image.shape[1] > max_widths[change_file["filepath"]]:
            max_widths[change_file["filepath"]] = code_image.shape[1]
            max_width_indices[change_file["filepath"]] = file_index
    logger.info("Done.")
    return max_width_indices


def get_font_size(change_file, resolution, type):
    logger.info(f"Determining font size for: {change_file['filepath']} for {resolution['name']} {type}")
    header_size = add_header(change_file)
    extended_content = add_filler_lines(change_file)
    longest_line = max([len(line) for line in extended_content.split("\n")])
    max_code_height = resolution["dimensions"][1] - header_size[1]

    high = min(500 * (20 / longest_line), 500)
    low = 0
    precision = 1
    font_size = (high + low) / 2
    best = low
    while high - low > precision:
        font_size = (high + low) / 2
        code_image = np.frombuffer(
            highlight_code(extended_content, change_file["language"], font_size=font_size), dtype=np.uint8
        )
        code_image = cv2.imdecode(code_image, cv2.IMREAD_UNCHANGED)
        code_image_width = code_image.shape[1]
        code_image_height = code_image.shape[0]
        wrap_count = math.ceil(code_image_height / max_code_height)
        wrap_width = wrap_count * code_image_width
        if wrap_width >= resolution["dimensions"][0]:
            high = math.floor(font_size)
        else:
            best = math.floor(font_size)
            low = math.floor(font_size)

    return (change_file['filepath'], f"{resolution['name']}_{type}", best - 1)


def get_change_files(config):
    changes_dir = os.path.expanduser(os.path.join(config.get("output_dir"), "changes"))
    change_filenames = sorted(glob.glob(os.path.join(changes_dir, f"*")))
    if not change_filenames:
        logger.error("No change files found.")
        exit(1)
    change_files = [json.load(open(change_filename, "r")) for change_filename in change_filenames]

    change_files = preprocess_change_files(config, change_files)
    max_width_indices = get_widest_files(change_files)

    font_sizes = {}

    starmap_args = []
    with multiprocessing.Pool(processes=None if config.get("multi_processing") else 1) as pool:
        for max_char_index in max_width_indices.values():
            change_file = change_files[max_char_index]
            if config.get("video"):
                starmap_args.extend(
                    [(change_file, resolution, "video") for resolution in config.get("video_resolutions")]
                )
            if config.get("gifs"):
                starmap_args.extend([(change_file, resolution, "gif") for resolution in config.get("gif_resolutions")])

        logger.info("Fitting font sizes to desired resolutions...")
        for filepath, resolution_name, font_size in tqdm(
            pool.starmap(get_font_size, starmap_args), total=len(starmap_args)
        ):
            font_sizes.setdefault(filepath, {})[resolution_name] = font_size

    change_files = [{**change_file, "font_size": font_sizes[change_file['filepath']]} for change_file in change_files]

    if change_files:
        return change_files
    else:
        return None


def create_media():
    from time import time

    start_time = time()
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

    logger.info(f"Finished creating media in {time() - start_time} seconds.")


if __name__ == "__main__":
    create_media()
