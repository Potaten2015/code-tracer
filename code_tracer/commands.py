import argparse
import json
import os
import glob
import video_creator


def init_config_file():
    # Prompt the user to select a project directory
    project_dir = input('Enter the path to the project directory: ')

    # Check if the path is valid
    if not os.path.exists(project_dir):
        print('Error: Invalid path.')
        return

    # Ask for the output folder location
    default_output_folder = os.path.expanduser('~/.code_tracer/')
    output_folder = (
        input(f"Enter the output folder location (default: {default_output_folder}): ").strip() or default_output_folder
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
                            watch_items.append(os.path.join(selection_path, '*'))
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
    interval = int(input('Enter the interval to check for changes (in seconds): '))
    name = input('Enter the project name: ')

    # Create the configuration dictionary
    config = {
        'watch': watch_items,
        'ignore': [item.strip() for item in ignore_items],
        'interval': interval,
        'name': name,
        'output_folder': output_folder,
    }

    # Write the configuration to the file
    config_filepath = os.path.join(project_dir, 'config.json')
    with open(config_filepath, 'w') as f:
        json.dump(config, f, indent=4)

    print('Config file created successfully!')


def generate_video():
    project_dir = input("Enter the path to the project directory: ")
    config_filepath = os.path.join(project_dir, "config.json")
    with open(config_filepath, "r") as f:
        config = json.load(f)

    video_creator.create_video(config)


if __name__ == '__main__':
    # Create the argument parser
    parser = argparse.ArgumentParser(description='CLI tool to initialize the config.json file.')

    # Add the init subcommand
    subparsers = parser.add_subparsers(dest='command')
    init_parser = subparsers.add_parser('init', help='Initialize the config.json file.')
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
