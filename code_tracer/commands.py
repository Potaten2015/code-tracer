import argparse
import json
import os
import glob
from video_creator import create_media
from utils import logger
from constants import DEFAULTS


def init_config_file():
    # Prompt the user to select a project directory
    project_dir = input('Enter the path to the project directory: ')
    project_dir = os.path.expanduser(project_dir)

    # Check if the path is valid
    if not os.path.exists(project_dir):
        print('Error: Invalid path.')
        return

    # Ask for the output folder location
    default_output_dir = os.path.join(project_dir, 'output')
    output_dir = (
        input(f'Enter the output folder location (default: {default_output_dir}): ').strip() or default_output_dir
    )

    # Check if the path is a file or directory
    if os.path.isfile(project_dir):
        # Use the directory containing the file as the project directory
        project_dir = os.path.dirname(project_dir)

    # Create the configuration dictionary
    watch_items = []
    while True:
        print(f'Select a directory or file to watch (current directory: {project_dir}):')
        options = glob.glob(os.path.join(project_dir, '*'))
        options.sort()
        for i, option in enumerate(options):
            if os.path.isdir(option):
                print(f'{i + 1}. {os.path.basename(option)}')
            else:
                print(f'{i + 1}. {os.path.basename(option)} (watch)')
        print('0. Done')
        selection = input('Enter a number: ')
        try:
            selection = int(selection)
            if selection == 0:
                break
            selection_path = options[selection - 1]
            if os.path.isdir(selection_path):
                # If the selection is a directory, prompt the user to select files or all files
                while True:
                    print(f'Select a file to watch or choose an option:')
                    files = glob.glob(os.path.join(selection_path, '*'))
                    files.sort()
                    for i, file in enumerate(files):
                        print(f'{i + 1}. {os.path.basename(file)}')
                    print(f'{len(files) + 1}. All files')
                    print('0. Back')
                    selection = input('Enter a number: ')
                    try:
                        selection = int(selection)
                        if selection == 0:
                            break
                        if selection == len(files) + 1:
                            watch_items.append(os.path.join(selection_path, '**'))
                            break
                        selection_path = files[selection - 1]
                        if os.path.isfile(selection_path):
                            watch_items.append(selection_path)
                            break
                    except (ValueError, IndexError):
                        print('Invalid selection.')
            else:
                # If the selection is a file, add it to the watch list
                watch_items.append(selection_path)
        except (ValueError, IndexError):
            print('Invalid selection.')

    ignore_items = input('Enter directories or files to ignore, separated by commas: ').split(',')
    ignore_items.extend(DEFAULTS['ignore'])
    interval = int(input('Enter the interval to check for changes (in seconds): '))
    video_length = int(input('Enter desired video length (in seconds): '))
    github_username = input('Enter GitHub username: ')
    name = input('Enter the project name: ')
    context_filepath = os.path.join(project_dir, 'context.txt')

    # Create the configuration dictionary
    config = {
        **DEFAULTS,
        'watch': watch_items,
        'ignore': [item.strip() for item in ignore_items],
        'interval': interval,
        'name': name,
        'output_dir': output_dir,
        'video_length': video_length,
        'github_username': github_username,
        'context_filepath': context_filepath,
    }

    # Write the configuration to the file
    config_filepath = os.path.join(project_dir, 'tracer.json')
    
    with open(config_filepath, 'w') as f:
        json.dump(config, f, indent=4)

    with open(context_filepath, 'w') as f:
        f.write("This is the context that is passed to the GPT model for manuscript generation.")

    logger.info("Configuration file created successfully.")


def generate_video():
    create_media()


if __name__ == '__main__':
    # Create the argument parser
    parser = argparse.ArgumentParser(description='CLI tool to initialize the tracer.json file.')

    # Add the init subcommand
    subparsers = parser.add_subparsers(dest='command')
    init_parser = subparsers.add_parser('init', help='Initialize the tracer.json file.')
    generate_video_parser = subparsers.add_parser(
        "generate_video", help="Generate a video from the saved code changes."
    )

    # Parse the arguments

    args = parser.parse_args()

    # Call the appropriate function based on the command
    if args.command == 'init':
        init_config_file()
    elif args.command == 'generate_video':
        generate_video()
    else:
        parser.print_help()
