import os
import sys
import fnmatch


def format_size(size):
    if size < 1024:
        return str(size) + " B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    else:
        return f"{size / (1024 * 1024):.1f} MB"


# Steps 14 + 15: filter, then sort (folders first, a-z, ignore case)
def get_entries(folder, names, no_files, exts, pattern):
    folders = []
    files = []
    for name in names:
        full_path = os.path.join(folder, name)
        if os.path.isdir(full_path):
            folders.append(name)
        elif not no_files:
            if exts and not name.lower().endswith(tuple(exts)):
                continue
            if pattern and not fnmatch.fnmatch(name, pattern):
                continue
            files.append(name)
    folders.sort(key=str.lower)
    files.sort(key=str.lower)
    return folders + files


def print_tree(folder, depth, prefix, counts, max_depth,
               no_files, exts, pattern, visited):
    # Step 12: handle folders we are not allowed to open
    try:
        names = os.listdir(folder)
    except PermissionError:
        print(prefix + "└── [access denied]")
        return

    entries = get_entries(folder, names, no_files, exts, pattern)

    for index in range(len(entries)):
        name = entries[index]
        full_path = os.path.join(folder, name)
        is_link = os.path.islink(full_path)

        if index == len(entries) - 1:
            connector = "└── "
            extension = "    "
        else:
            connector = "├── "
            extension = "│   "

        if os.path.isdir(full_path):
            counts[0] += 1
            label = name + "/"
            if is_link:  # Step 13: mark symlinks clearly
                label += " -> " + os.readlink(full_path) + " [symlink]"
            print(prefix + connector + label)

            if max_depth is None or depth < max_depth:
                real = os.path.realpath(full_path)
                if real in visited:  # Step 13: loop protection
                    print(prefix + extension + "[symlink loop skipped]")
                else:
                    visited.append(real)
                    print_tree(full_path, depth + 1, prefix + extension,
                               counts, max_depth, no_files,
                               exts, pattern, visited)
        else:
            try:
                size = os.path.getsize(full_path)
            except OSError:  # broken symlink etc.
                size = 0
            counts[1] += 1
            counts[2] += size
            label = name
            if is_link:
                label += " -> " + os.readlink(full_path) + " [symlink]"
            print(prefix + connector + label + "   " + format_size(size))


# ---- main program ----
root = input("Root folder: ")

if not os.path.exists(root):
    print("Error: folder does not exist.")
    sys.exit(1)
if not os.path.isdir(root):
    print("Error: that path is not a folder.")
    sys.exit(1)
if not os.access(root, os.R_OK):
    print("Error: no permission to read that folder.")
    sys.exit(1)

depth_text = input("Max depth (press Enter for no limit): ")
if depth_text == "":
    max_depth = None
else:
    try:
        max_depth = int(depth_text)
    except ValueError:
        print("Error: max depth must be a whole number.")
        sys.exit(1)

show_files = input("Show files (y/n): ")
no_files = show_files.lower() == "n"

ext_text = input("Extensions e.g. .py,.json (Enter for all): ")
exts = []
if ext_text != "":
    for e in ext_text.split(","):
        exts.append(e.strip().lower())

pattern = input("Name pattern e.g. test_* (Enter for none): ")

counts = [0, 0, 0]
visited = [os.path.realpath(root)]
print(root + "/")
print_tree(root, 0, "", counts, max_depth, no_files, exts, pattern, visited)
print(f"{counts[0]} folders, {counts[1]} files, total {format_size(counts[2])}")
