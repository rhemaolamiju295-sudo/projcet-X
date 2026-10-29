import os
import sys
import csv
import fnmatch
import argparse


# ---------- small helpers ----------

def format_size(size):
    if size < 1024:
        return str(size) + " B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    else:
        return f"{size / (1024 * 1024):.1f} MB"


def split_list(text, lower=False):
    # "a, b,c" -> ["a", "b", "c"]
    items = []
    if text != "":
        for part in text.split(","):
            part = part.strip()
            if part != "":
                if lower:
                    part = part.lower()
                items.append(part)
    return items


def is_excluded(name, exclude):
    for pattern in exclude:
        if fnmatch.fnmatch(name, pattern):
            return True
    return False


def check_folder(path):
    if not os.path.exists(path):
        print(f"Error: {path} does not exist.")
        sys.exit(1)
    if not os.path.isdir(path):
        print(f"Error: {path} is not a folder.")
        sys.exit(1)
    if not os.access(path, os.R_OK):
        print(f"Error: no permission to read {path}.")
        sys.exit(1)


# ---------- item 16: folder sizes, each folder visited once ----------

def compute_sizes(folder, exclude, sizes):
    # post-order: children first, then the folder adds them up.
    # every folder's total is saved in the sizes dict, so the
    # tree printer just looks it up (no re-walking).
    total = 0
    try:
        names = os.listdir(folder)
    except OSError:
        sizes[folder] = 0
        return 0

    for name in names:
        if is_excluded(name, exclude):
            continue
        full_path = os.path.join(folder, name)
        if os.path.isdir(full_path):
            if os.path.islink(full_path):
                continue  # symlinked folders are not counted in sizes
            total += compute_sizes(full_path, exclude, sizes)
        else:
            try:
                total += os.path.getsize(full_path)
            except OSError:
                pass

    sizes[folder] = total
    return total


# ---------- tree printing (levels 1 to 3 + exclude) ----------

def get_entries(folder, names, opt):
    folders = []
    files = []
    for name in names:
        if is_excluded(name, opt["exclude"]):  # item 20
            continue
        full_path = os.path.join(folder, name)
        if os.path.isdir(full_path):
            folders.append(name)
        elif opt["show_files"]:
            if opt["exts"] and not name.lower().endswith(tuple(opt["exts"])):
                continue
            if opt["pattern"] and not fnmatch.fnmatch(name, opt["pattern"]):
                continue
            files.append(name)
    folders.sort(key=str.lower)
    files.sort(key=str.lower)
    return folders + files


def print_tree(folder, depth, prefix, counts, opt, ancestors):
    try:
        names = os.listdir(folder)
    except PermissionError:
        print(prefix + "└── [access denied]")
        return
    except OSError:
        print(prefix + "└── [cannot read]")
        return

    entries = get_entries(folder, names, opt)

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
            if opt["sizes"] is not None and full_path in opt["sizes"]:
                label += "   " + format_size(opt["sizes"][full_path])
            if is_link:
                label += " -> " + os.readlink(full_path) + " [symlink]"
            print(prefix + connector + label)

            if opt["max_depth"] is None or depth < opt["max_depth"]:
                real = os.path.realpath(full_path)
                if real in ancestors:  # item 13: loop protection
                    print(prefix + extension + "└── [symlink loop skipped]")
                else:
                    ancestors.append(real)  # item 19: only the current path stack
                    print_tree(full_path, depth + 1, prefix + extension,
                               counts, opt, ancestors)
                    ancestors.pop()
        else:
            try:
                size = os.path.getsize(full_path)
            except OSError:
                size = 0
            counts[1] += 1
            counts[2] += size
            label = name
            if is_link:
                label += " -> " + os.readlink(full_path) + " [symlink]"
            print(prefix + connector + label + "   " + format_size(size))


# ---------- item 17: --summary (CSV) ----------

def summarize(folder, rel, depth, writer, exclude):
    # writes one CSV row per folder (after its children are done)
    # and returns the numbers the parent needs.
    files = 0
    total = 0
    largest_path = ""
    largest_size = -1
    deepest_path = rel
    deepest_depth = depth

    try:
        names = os.listdir(folder)
    except OSError:
        names = []
    names.sort(key=str.lower)

    for name in names:
        if is_excluded(name, exclude):
            continue
        full_path = os.path.join(folder, name)
        if rel == ".":
            child_rel = name
        else:
            child_rel = os.path.join(rel, name)

        if os.path.isdir(full_path):
            if os.path.islink(full_path):
                continue
            c_files, c_total, c_lpath, c_lsize, c_dpath, c_ddepth = summarize(
                full_path, child_rel, depth + 1, writer, exclude)
            files += c_files
            total += c_total
            if c_lsize > largest_size:
                largest_size = c_lsize
                largest_path = c_lpath
            if c_ddepth > deepest_depth:
                deepest_depth = c_ddepth
                deepest_path = c_dpath
        else:
            try:
                size = os.path.getsize(full_path)
            except OSError:
                size = 0
            files += 1
            total += size
            if size > largest_size:
                largest_size = size
                largest_path = child_rel
            if depth + 1 > deepest_depth:
                deepest_depth = depth + 1
                deepest_path = child_rel

    shown_largest = largest_size
    if shown_largest < 0:
        shown_largest = 0
    writer.writerow([rel, files, total, largest_path, shown_largest, deepest_path])
    return files, total, largest_path, largest_size, deepest_path, deepest_depth


# ---------- item 18: --compare ----------

def collect_files(folder, rel, found, exclude):
    try:
        names = os.listdir(folder)
    except OSError:
        return
    for name in names:
        if is_excluded(name, exclude):
            continue
        full_path = os.path.join(folder, name)
        if rel == "":
            child_rel = name
        else:
            child_rel = os.path.join(rel, name)

        if os.path.isdir(full_path):
            if not os.path.islink(full_path):
                collect_files(full_path, child_rel, found, exclude)
        else:
            try:
                info = os.stat(full_path)
            except OSError:
                continue
            found[child_rel] = (info.st_size, int(info.st_mtime))


def compare_folders(folder_a, folder_b, exclude):
    files_a = {}
    files_b = {}
    collect_files(folder_a, "", files_a, exclude)
    collect_files(folder_b, "", files_b, exclude)

    only_a = []
    only_b = []
    changed = []

    for path in sorted(files_a, key=str.lower):
        if path not in files_b:
            only_a.append(path)
        else:
            size_a, time_a = files_a[path]
            size_b, time_b = files_b[path]
            if size_a != size_b:
                changed.append(path + "   size " + format_size(size_a)
                               + " -> " + format_size(size_b))
            elif time_a != time_b:
                changed.append(path + "   modified time differs")

    for path in sorted(files_b, key=str.lower):
        if path not in files_a:
            only_b.append(path)

    print(f"Comparing A = {folder_a}  and  B = {folder_b}")
    print()
    print(f"Only in A ({len(only_a)}):")
    for path in only_a:
        print("  - " + path)
    print()
    print(f"Only in B ({len(only_b)}):")
    for path in only_b:
        print("  + " + path)
    print()
    print(f"Changed ({len(changed)}):")
    for line in changed:
        print("  ~ " + line)


# ---------- main program: read settings ----------

parser = argparse.ArgumentParser(description="Directory tree printer")
parser.add_argument("root", nargs="?")
parser.add_argument("--max-depth", type=int, default=None)
parser.add_argument("--files", action=argparse.BooleanOptionalAction, default=True)
parser.add_argument("--ext", default="")
parser.add_argument("--pattern", default="")
parser.add_argument("--exclude", default="")
parser.add_argument("--summary", action="store_true")
parser.add_argument("--compare", metavar="OTHER_FOLDER", default=None)
parser.add_argument("--stream", action="store_true")
args = parser.parse_args()

if args.root is None:
    # no options typed: ask with prompts
    root = input("Root folder: ")
    mode = input("Mode - tree, summary or compare (Enter = tree): ").strip().lower()
    if mode == "":
        mode = "tree"
    if mode not in ("tree", "summary", "compare"):
        print("Error: mode must be tree, summary or compare.")
        sys.exit(1)

    other = None
    if mode == "compare":
        other = input("Second folder: ")

    exclude_text = input("Exclude e.g. .git,__pycache__,*.log (Enter for none): ")

    max_depth = None
    show_files = True
    ext_text = ""
    pattern = ""
    stream = False

    if mode == "tree":
        depth_text = input("Max depth (Enter for no limit): ")
        if depth_text != "":
            try:
                max_depth = int(depth_text)
            except ValueError:
                print("Error: max depth must be a whole number.")
                sys.exit(1)
        show_files = input("Show files (y/n): ").strip().lower() != "n"
        ext_text = input("Extensions e.g. .py,.json (Enter for all): ")
        pattern = input("Name pattern e.g. test_* (Enter for none): ")
        stream = input("Stream mode, no folder sizes (y/n, Enter = n): ").strip().lower() == "y"
else:
    root = args.root
    other = args.compare
    if args.compare is not None:
        mode = "compare"
    elif args.summary:
        mode = "summary"
    else:
        mode = "tree"
    exclude_text = args.exclude
    max_depth = args.max_depth
    show_files = args.files
    ext_text = args.ext
    pattern = args.pattern
    stream = args.stream

exts = split_list(ext_text, True)
exclude = split_list(exclude_text)

# ---------- run the chosen mode ----------

check_folder(root)

if mode == "summary":
    writer = csv.writer(sys.stdout, lineterminator="\n")
    writer.writerow(["folder", "files", "total_bytes",
                     "largest_file", "largest_bytes", "deepest_path"])
    summarize(root, ".", 0, writer, exclude)

elif mode == "compare":
    check_folder(other)
    compare_folders(root, other, exclude)

else:
    sizes = None
    if not stream:
        sizes = {}
        compute_sizes(root, exclude, sizes)

    opt = {
        "max_depth": max_depth,
        "show_files": show_files,
        "exts": exts,
        "pattern": pattern,
        "exclude": exclude,
        "sizes": sizes,
    }

    counts = [0, 0, 0]
    shown = root.rstrip("/") or root
    header = shown + "/"
    if sizes is not None:
        header += "   " + format_size(sizes[root])
    print(header)
    print_tree(root, 0, "", counts, opt, [os.path.realpath(root)])
    print(f"{counts[0]} folders, {counts[1]} files, total {format_size(counts[2])}")
