import os


def format_size(size):
    if size < 1024:
        return str(size) + " B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    else:
        return f"{size / (1024 * 1024):.1f} MB"


def print_tree(folder, depth, prefix, counts, max_depth, no_files):
    names = os.listdir(folder)
    names.sort()  # temporary plain sort, proper sorting comes in Step 15

    visible = []
    for name in names:
        full_path = os.path.join(folder, name)
        if not no_files or os.path.isdir(full_path):
            visible.append(name)

    for index in range(len(visible)):
        name = visible[index]
        full_path = os.path.join(folder, name)

        if index == len(visible) - 1:
            connector = "└── "
            extension = "    "
        else:
            connector = "├── "
            extension = "│   "

        if os.path.isdir(full_path):
            counts[0] += 1
            print(prefix + connector + name + "/")
            if max_depth is None or depth < max_depth:
                print_tree(full_path, depth + 1, prefix + extension,
                           counts, max_depth, no_files)
        else:
            size = os.path.getsize(full_path)
            counts[1] += 1
            counts[2] += size
            print(prefix + connector + name + "   " + format_size(size))


root = input("Root folder: ")

depth_text = input("Max depth (press Enter for no limit): ")
if depth_text == "":
    max_depth = None
else:
    max_depth = int(depth_text)

show_files = input("Show files (y/n): ")
no_files = show_files.lower() == "n"

counts = [0, 0, 0]
print(root + "/")
print_tree(root, 0, "", counts, max_depth, no_files)
print(f"{counts[0]} folders, {counts[1]} files, total {format_size(counts[2])}")
