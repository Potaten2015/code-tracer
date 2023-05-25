import fnmatch
import os
import json
import time
import glob
from utils import Config, logger
from constants import TIME_FORMAT


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


def get_language(filepath):
    file_extension = os.path.splitext(filepath)[-1]
    return SUPPORTED_LANGUAGES.get(file_extension, "text")


def is_ignored(path, ignore_items):
    for ignore_item in ignore_items:
        if fnmatch.fnmatch(path, ignore_item):
            return True
    return False


def expand_wildcards(paths, config):
    expanded_paths = []
    ignore_items = config.get("ignore", [])
    ignore_items = [os.path.expanduser(os.path.join(config.get("project_dir"), item)) for item in ignore_items]
    for path in paths:
        if '*' in path:
            new_paths = glob.glob(path, include_hidden=True)
            for new_path in new_paths:
                if ".traceignore" in path:
                    with open(new_path, 'r') as f:
                        traceignore = f.read().splitlines()
                    config.append("ignore", [os.path.join(os.path.dirname(new_path), item) for item in traceignore])
            for new_path in new_paths:
                if os.path.isdir(new_path):
                    expanded_paths += expand_wildcards([os.path.join(new_path, '*')], config)
                else:
                    expanded_paths += expand_wildcards([new_path], config)
        elif os.path.isdir(path):
            expanded_paths += expand_wildcards([os.path.join(path, '*')], config)
        else:
            if not is_ignored(path, ignore_items):
                expanded_paths.append(path)
    return expanded_paths


def remove_ignored(config):
    ignored = config.get("ignore")

    output_dir = os.path.expanduser(os.path.join(config.get("output_dir")))
    changes_dir = os.path.join(output_dir, "changes")
    change_filenames = glob.glob(os.path.join(changes_dir, "*"), recursive=True, include_hidden=True)
    for change_filename in change_filenames:
        for ignore_item in ignored:
            if fnmatch.fnmatch(change_filename, ignore_item):
                try:
                    os.remove(change_filename)
                    logger.info(f"Removed history for {change_filename}")
                except:
                    logger.warning(f"Unable to remove history file for {change_filename}")


def get_items(key, config):
    items = config.get(key)
    items = [os.path.expanduser(item) for item in items]
    items = [os.path.join(config.get("project_dir"), item) for item in items]
    items = expand_wildcards(items, config)
    return items


def watch_directories():
    project_dir = os.path.expanduser(input('Enter the path to the project directory: '))
    config_filepath = os.path.join(project_dir, 'tracer.json')
    config = Config(config_filepath)

    config.set("project_dir", project_dir)
    watch_items = get_items('watch', config)
    remove_ignored(config)
    logger.info(f'Watching {len(watch_items)} items.')

    # Get the project name
    project_name = config.get("name")

    # Get the output folder from the config
    output_dir = os.path.expanduser(config.get("output_dir"))

    # Create the output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Initialize a dictionary to store the modification times of the watched files
    last_modified_times = {}

    # Initialize a list to store the unreadable files
    unreadable_files = []

    # Initialize a variable to store the total size of the copied files
    total_size = 0

    # Log that the script has started
    logger.info('Code Tracer script started.')

    # Start the watch loop
    try:
        while True:
            for item in watch_items:
                if file_has_changed(item, last_modified_times):
                    try:
                        timestamp = time.strftime(TIME_FORMAT)
                        size_changed = copy_file(item, output_dir, timestamp, project_name, config)
                        total_size += size_changed
                    except UnicodeDecodeError:
                        unreadable_files.append(item)
                        logger.warning(f'Unable to read file {item}.')

            # Wait for the specified interval before checking for changes again
            time.sleep(config.get("interval"))

    except KeyboardInterrupt:
        # Log that the script has stopped
        logger.info('Code Tracer stopped.')

        # Display the unreadable files
        if unreadable_files:
            logger.warning(f'Unable to read {len(unreadable_files)} files:')
            for file in unreadable_files:
                logger.warning(f'- {file}')

        # Display the storage used by the copied files
        logger.info(f'Total storage used: {human_readable_size(total_size)}')


# Define the function to check if a file has changed since it was last checked
def file_has_changed(filepath, last_modified_times):
    # Check if the file has been seen before
    if filepath in last_modified_times:
        # Check if the modification time has changed
        if os.path.getmtime(filepath) > last_modified_times[filepath]:
            # Update the modification time
            last_modified_times[filepath] = os.path.getmtime(filepath)
            return True
    else:
        # Add the file to the dictionary
        last_modified_times[filepath] = os.path.getmtime(filepath)
        return True

    return False


def copy_file(filepath, output_dir, timestamp, project_name, config):
    language = get_language(filepath)

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    changes_dir = os.path.join(output_dir, "changes")
    os.makedirs(changes_dir, exist_ok=True)

    updated_filepath = filepath.replace(os.path.sep, "__")
    change_filename = f"{timestamp}_{updated_filepath}.json"
    change_filepath = os.path.join(changes_dir, change_filename)

    data = {
        "filepath": updated_filepath,
        "language": language,
        "content": content,
        "project_name": project_name,
        "github_username": config.get("github_username"),
    }

    with open(change_filepath, "w", encoding="utf-8") as f:
        json.dump(data, f)

    # Log that the file has been saved
    logger.info(f'File {filepath} updates saved to {change_filepath}.')

    # Calculate the size of the new file
    new_file_size = os.path.getsize(change_filepath)

    return new_file_size


# Define the function to convert a size in bytes to a human-readable string
def human_readable_size(size):
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    unit_index = 0
    while size > 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    return f'{size:.2f} {units[unit_index]}'


# Run the watch_directories function
if __name__ == '__main__':
    watch_directories()
