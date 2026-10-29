import os


def print_tree(folder, depth, counts, max_depth, no_files):
    indent = "    " * depth
    names = os.listdir(folder)
    for i in names:
        full_path = os.path.join(folder, i)

        if os.path.isdir(full_path):
            counts[0] += 1
            print(indent + i + "/")
            if max_depth is None or depth < max_depth:
                print_tree(full_path, depth + 1, counts, max_depth, no_files)
        else:
            if not no_files:
                counts[1] += 1
                print(indent + i)


root = input("Root folder: ")

depth_text = input("Max depth (press Enter for no limit): ")
if depth_text == "":
    max_depth = None
else:
    max_depth = int(depth_text)

show_files = input("Show files (y/n): ")
no_files = show_files.lower() == "n"

counts = [0, 0]
print_tree(root, 0, counts, max_depth, no_files)
print(f"{counts[0]} folders, {counts[1]} files")
