import os
import shutil


def save_stac_files(source_dir='wpstac', output_dir='worldpop_files'):
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Walk through source directory
    for root, _, files in os.walk(source_dir):
        for file in files:
            if file.endswith('.py'):
                # Get original file path
                source_path = os.path.join(root, file)
                # Get relative path from wpstac directory
                rel_path = os.path.relpath(source_path, source_dir)
                # Create new filename with worldpop prefix
                new_filename = f'worldpop-{rel_path.replace(os.sep, "-")}'
                # Create destination path
                dest_path = os.path.join(output_dir, new_filename)

                # Copy file with new name
                shutil.copy2(source_path, dest_path)
                print(f'Saved: {new_filename}')


if __name__ == '__main__':
    save_stac_files()