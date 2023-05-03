import fnmatch
import os
import json
import time
import logging
import glob
from video_creator import get_language

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')


def is_ignored(path, ignore_items):
    for ignore_item in ignore_items:
        if fnmatch.fnmatch(path, ignore_item):
            return True
    return False


def expand_wildcards(paths, config):
    expanded_paths = []
    ignore_items = config["ignore"]
    ignore_items = [os.path.join(config["project_dir"], item) for item in ignore_items]
    for path in paths:
        if '*' in path:
            new_paths = glob.glob(path, include_hidden=True)
            for path in new_paths:
                if ".traceignore" in path:
                    with open(path, 'r') as f:
                        traceignore = f.read().splitlines()
                    config["ignore"] += [os.path.join(os.path.dirname(path), item) for item in traceignore]
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


def get_items(key, config):
    items = config[key]
    items = [os.path.join(config["project_dir"], item) for item in items]
    items = expand_wildcards(items, config)
    return items


# Define the function to watch the directories/files
def watch_directories():
    # Load the configuration file
    project_dir = input('Enter the path to the project directory: ')
    config_filepath = os.path.join(project_dir, 'config.json')
    with open(config_filepath, 'r') as f:
        config = json.load(f)

    config['project_dir'] = project_dir
    # Get the directories/files to watch/ignore
    watch_items = get_items('watch', config)
    logging.info(f'Watching {len(watch_items)} items.')

    # Get the project name
    project_name = config['name']

    # Get the output folder from the config
    output_folder = config['output_folder']

    # Create the output directory if it doesn't exist
    output_dir = os.path.expanduser(os.path.join(output_folder, project_name))
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Initialize a dictionary to store the modification times of the watched files
    last_modified_times = {}

    # Initialize a list to store the unreadable files
    unreadable_files = []

    # Initialize a variable to store the total size of the copied files
    total_size = 0

    # Log that the script has started
    logging.info('Code Tracer script started.')

    # Start the watch loop
    try:
        while True:
            for item in watch_items:
                if file_has_changed(item, last_modified_times):
                    try:
                        timestamp = time.strftime('%Y%m%d-%H%M%S')
                        lines_changed, size_changed = copy_file(item, output_dir, timestamp, project_name)
                        total_size += size_changed
                        logging.info(f'File {item} has changed. {lines_changed} lines changed.')
                    except UnicodeDecodeError:
                        unreadable_files.append(item)
                        logging.warning(f'Unable to read file {item}.')

            # Wait for the specified interval before checking for changes again
            time.sleep(config['interval'])

    except KeyboardInterrupt:
        # Log that the script has stopped
        logging.info('Code Tracer script stopped.')

        # Display the unreadable files
        if unreadable_files:
            logging.warning(f'Unable to read {len(unreadable_files)} files:')
            for file in unreadable_files:
                logging.warning(f'- {file}')

        # Display the storage used by the copied files
        logging.info(f'Total storage used: {human_readable_size(total_size)}')


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


def copy_file(file_path, project_dir, timestamp, project_name):
    file_name = os.path.basename(file_path)

    language = get_language(file_name)

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    data = {"filename": file_name, "language": language, "content": content, "project_name": project_name}

    changes_dir = os.path.join(project_dir, "changes")
    os.makedirs(changes_dir, exist_ok=True)

    change_filename = f"{timestamp}_{file_name}.json"
    change_file_path = os.path.join(changes_dir, change_filename)

    # Get the previous change file if it exists
    prev_change_file = get_previous_change_file(changes_dir, file_name)

    if prev_change_file:
        with open(prev_change_file, "r", encoding="utf-8") as f:
            prev_data = json.load(f)
            prev_content = prev_data["content"]
    else:
        prev_content = ""

    # Count the difference in lines between the new and old files
    lines_changed = len(content.splitlines()) - len(prev_content.splitlines())

    with open(change_file_path, "w", encoding="utf-8") as f:
        json.dump(data, f)

    # Log that the file has been saved
    logging.info(f'File {file_path} saved to {change_file_path} ({lines_changed} lines changed).')

    # Calculate the size of the new file
    new_file_size = os.path.getsize(change_file_path)

    return lines_changed, new_file_size


def get_previous_change_file(changes_dir, file_name):
    change_files = sorted(glob.glob(os.path.join(changes_dir, f"*_{file_name}.json")))

    if change_files:
        return change_files[-1]
    else:
        return None


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
