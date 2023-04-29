import fnmatch
import os
import json
import shutil
import time
import datetime
import logging
import glob
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def is_ignored(path, patterns):
    for pattern in patterns:
        if fnmatch.fnmatch(path, pattern):
            return True
    return False


# Define the function to watch the directories/files
def watch_directories():
    # Load the configuration file
    project_dir = input('Enter the path to the project directory: ')
    config_filepath = os.path.join(project_dir, 'config.json')
    with open(config_filepath, 'r') as f:
        config = json.load(f)

    # Get the directories/files to watch/ignore
    watch_items = config['watch']
    ignore_items = config['ignore']

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
                # Check if the item is in the ignore list
                if is_ignored(item, ignore_items):
                    continue

                # Check if the item is a directory
                if os.path.isdir(item):
                    for root, dirs, files in os.walk(item):
                        # Check for a .traceignore file in the directory
                        traceignore_path = os.path.join(root, '.traceignore')
                        if os.path.exists(traceignore_path):
                            with open(traceignore_path, 'r') as f:
                                traceignore = f.read().splitlines()
                            ignore_items += [os.path.join(root, pattern) for pattern in traceignore]
                        dirs[:] = [d for d in dirs if not is_ignored(os.path.join(root, d), ignore_items)]
                        for filename in files:
                            filepath = os.path.join(root, filename)
                            if file_has_changed(filepath, last_modified_times):
                                try:
                                    lines_changed, size_changed = copy_file(filepath, output_dir)
                                    total_size += size_changed
                                    logging.info(f'File {filepath} has changed. {lines_changed} lines changed.')
                                except UnicodeDecodeError:
                                    unreadable_files.append(filepath)
                                    logging.warning(f'Unable to read file {filepath}.')
                # Check if the item is a file
                elif os.path.isfile(item):
                    if file_has_changed(item, last_modified_times):
                        try:
                            lines_changed, size_changed = copy_file(item, output_dir)
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


# Define the function to copy the file to the output directory
def copy_file(filepath, output_dir):
    # Get the modification time of the file
    modified_time = datetime.datetime.fromtimestamp(os.path.getmtime(filepath))

    # Create the output filename
    output_filename = f'{modified_time.strftime("%Y.%m.%d-%H:%M:%S")}.txt'
    output_path = os.path.join(output_dir, output_filename)

    # Copy the file to the output directory
    encodings = ['utf-8', 'iso-8859-1', 'windows-1252']
    for encoding in encodings:
        try:
            with open(filepath, 'r', encoding=encoding) as f:
                with open(output_path, 'w') as f_out:
                    shutil.copyfileobj(f, f_out)

                # Count the number of lines in the file
                with open(filepath, 'r', encoding=encoding) as f:
                    lines_changed = len(f.readlines())

                # Log that the file has been saved
                logging.info(f'File {filepath} saved to {output_path} ({lines_changed} lines).')

                # Calculate the size of the copied file
                size_changed = os.path.getsize(output_path) - os.path.getsize(filepath)

                return lines_changed, size_changed
        except UnicodeDecodeError:
            continue

    # Log that the file is unreadable
    raise UnicodeDecodeError


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
