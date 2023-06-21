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


def expand_wildcards(paths):
    new_paths = []
    for path in paths:
        if os.path.isdir(path):
            new_paths.extend(glob.glob(os.path.join(path, "**"), recursive=True))
        elif "**" in path or "*" in path:
            new_paths.extend(glob.glob(path, recursive=True))
        else:
            new_paths.append(path)
    new_new_paths = []

    for path in new_paths:
        new_new_paths.append(path)
        if os.path.isdir(path):
            new_new_paths.extend(expand_wildcards(glob.glob(os.path.join(path, "**/.*"), recursive=True)))

    new_new_paths = [path for path in new_new_paths if os.path.isfile(path)]

    return new_new_paths


def remove_ignored(paths, config):
    ignored_paths = config.get("ignore")
    logger.info(
        "Removing"
        f" {len([path for path in paths if any([fnmatch.fnmatch(path, ignore) for ignore in ignored_paths])])} ignored"
        " paths"
    )
    return [path for path in paths if not any([fnmatch.fnmatch(path, ignore) for ignore in ignored_paths])]


def get_paths(key, config):
    logger.info(f"Getting {key} paths from config")
    items = config.get(key)
    items = [os.path.expanduser(item) for item in items]
    items = [os.path.join(config.get("project_dir"), item) for item in items]
    items = expand_wildcards(items)
    logger.info(f"Found {len(items)} expanded paths for config['{key}']")
    return items


def watch_directories():
    project_dir = os.path.expanduser(input('Enter the path to the project directory: '))
    config_filepath = os.path.join(project_dir, 'tracer.json')
    config = Config(config_filepath)
    logger.setLevel(config.get("log_level"))
    config.set("project_dir", project_dir, local=True)
    session = input(f"Enter the session name (leave blank for current: {config.get('session')}):  ")
    if session:
        config.set("session", session)
        config.append("all_sessions", session)
        config.write(config_filepath)

    watch_items = get_paths('watch', config)
    watch_items = remove_ignored(watch_items, config)
    logger.info(f'Watching {len(watch_items)} items.')
    logger.debug(f'Watch items: {watch_items}')

    # Get the project name
    project_name = config.get("name")

    # Get the output folder from the config
    output_dir = os.path.expanduser(config.get("output_dir"))

    # Create the output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, mode=0o777)

    # Initialize a dictionary to store the modification times of the watched files
    last_modified_times = {filepath: os.path.getmtime(filepath) for filepath in watch_items}

    # Initialize a list to store the unreadable files
    unreadable_files = []

    # Initialize a variable to store the total size of the copied files
    total_size = 0

    # Log that the script has started
    logger.info('Code Tracer script started.')
    logger.info('''
Always watching...
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣀⣤⣤⣤⣤⣴⣤⣤⣄⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⣀⣴⣾⠿⠛⠋⠉⠁⠀⠀⠀⠈⠙⠻⢷⣦⡀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⣤⣾⡿⠋⠁⠀⣠⣶⣿⡿⢿⣷⣦⡀⠀⠀⠀⠙⠿⣦⣀⠀⠀⠀⠀
⠀⠀⢀⣴⣿⡿⠋⠀⠀⢀⣼⣿⣿⣿⣶⣿⣾⣽⣿⡆⠀⠀⠀⠀⢻⣿⣷⣶⣄⠀
⠀⣴⣿⣿⠋⠀⠀⠀⠀⠸⣿⣿⣿⣿⣯⣿⣿⣿⣿⣿⠀⠀⠀⠐⡄⡌⢻⣿⣿⡷
⢸⣿⣿⠃⢂⡋⠄⠀⠀⠀⢿⣿⣿⣿⣿⣿⣯⣿⣿⠏⠀⠀⠀⠀⢦⣷⣿⠿⠛⠁
⠀⠙⠿⢾⣤⡈⠙⠂⢤⢀⠀⠙⠿⢿⣿⣿⡿⠟⠁⠀⣀⣀⣤⣶⠟⠋⠁⠀⠀⠀
⠀⠀⠀⠀⠈⠙⠿⣾⣠⣆⣅⣀⣠⣄⣤⣴⣶⣾⣽⢿⠿⠟⠋⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠉⠙⠛⠛⠙⠋⠉⠉⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
(https://emojicombos.com/eye-ascii-art)
''')

    # Start the watch loop
    try:
        start_time = time.time()
        while True:
            if time.time() - start_time > 60:
                logger.info("Reloading watch items...")
                watch_items = get_paths('watch', config)
                watch_items = remove_ignored(watch_items, config)
                logger.info(f'Watching {len(watch_items)} items.')
                logger.debug(f'Watch items: {watch_items}')
                start_time = time.time()
            for item in watch_items:
                if file_has_changed(item, last_modified_times):
                    if not os.path.exists(item):
                        watch_items.remove(item)
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
        if not os.path.exists(filepath):
            last_modified_times.pop(filepath)
            logger.warning(f"File {filepath} no longer not exists.")
            return True
        # Check if the modification time has changed
        if os.path.getmtime(filepath) > last_modified_times[filepath]:
            # Update the modification time
            last_modified_times[filepath] = os.path.getmtime(filepath)
            return True
    else:
        # Add the file to the dictionary
        if os.path.exists(filepath):
            last_modified_times[filepath] = os.path.getmtime(filepath)
        else:
            logger.warning(f"File {filepath} no longer not exists.")
        return True

    return False


def copy_file(filepath, output_dir, timestamp, project_name, config):
    language = get_language(filepath)

    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    else:
        content = ""

    changes_dir = os.path.join(output_dir, "changes")
    os.makedirs(changes_dir, exist_ok=True, mode=0o777)

    updated_filepath = filepath.replace(os.path.sep, "__")
    change_filename = f"{timestamp}{updated_filepath}.json"
    change_filepath = os.path.join(changes_dir, change_filename)

    data = {
        "filepath": updated_filepath,
        "language": language,
        "content": content,
        "project_name": project_name,
        "github_username": config.get("github_username"),
        "session": config.get("session"),
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
