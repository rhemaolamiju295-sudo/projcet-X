import os
import argparse 


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
parser = argparse.ArgumentParser(description ="Directory tree printer")
parser.add_argument("root")
parser.add_argument("--max-depth", type = int, default = None)
parser.add_argument("--no-files", action = "store_true")
args = parser.parse_args()

counts = [0, 0]
print_tree(args.root, 0, counts, args.max_depth, args.no_files)
print(f"{counts[0]} folders, {counts[1]} files")
