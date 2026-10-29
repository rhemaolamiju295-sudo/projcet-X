import os          # L1 step 2: listdir, path.join, isdir
import sys         # L3 step 11: sys.exit for bad input
import csv         # L4 item 17: CSV output
import fnmatch     # L3 step 14 and L4 item 20: glob patterns
import argparse    # L2 steps 7 and 8: command line options


# ================= HELPERS =================

# L2 step 10: bytes -> B / KB / MB
def format_size(size):
    if size < 1024:
        return str(size) + " B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    else:
        return f"{size / (1024 * 1024):.1f} MB"


# turns "a, b,c" into a list (used for --ext and --exclude)
def split_list(text, lower=False):
    items = []
    if text != "":
        for part in text.split(","):
            part = part.strip()
            if part != "":
                if lower:
                    part = part.lower()
                items.append(part)
    return items


# L4 item 20: True if the name matches any exclude pattern
def is_excluded(name, exclude):
    for pattern in exclude:
        if fnmatch.fnmatch(name, pattern):
            return True
    return False


# L3 step 11: validate the root folder (exists, is a folder, readable)
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


# ================= LEVEL 4 item 16: folder sizes =================

# walks the tree ONCE, children first, then adds up each folder.
# every total is saved in the sizes dict so print_tree just looks it up
# (no re-walking)
def compute_sizes(folder, exclude, sizes):
    total = 0
    try:
        names = os.listdir(folder)
    except OSError:
        sizes[folder] = 0
        return 0

    for name in names:
        if is_excluded(name, exclude):      # item 20: excluded = not counted
            continue
        full_path = os.path.join(folder, name)
        if os.path.isdir(full_path):
            if os.path.islink(full_path):   # item 13: don't follow symlinked folders
                continue
            total += compute_sizes(full_path, exclude, sizes)   # recursion
        else:
            try:
                total += os.path.getsize(full_path)
            except OSError:
                pass

    sizes[folder] = total
    return total


# ================= LEVEL 3 steps 14 + 15: filter and sort =================

# decides which entries get shown and in what order
def get_entries(folder, names, opt):
    folders = []
    files = []
    for name in names:
        if is_excluded(name, opt["exclude"]):   # L4 item 20
            continue
        full_path = os.path.join(folder, name)
        if os.path.isdir(full_path):            # L1 step 3: folder or file
            folders.append(name)
        elif opt["show_files"]:                 # L2 step 8: hide/show files
            # L3 step 14: extension filter
            if opt["exts"] and not name.lower().endswith(tuple(opt["exts"])):
                continue
            # L3 step 14: name pattern filter
            if opt["pattern"] and not fnmatch.fnmatch(name, opt["pattern"]):
                continue
            files.append(name)
    # L3 step 15: folders first, a-z, ignore case
    folders.sort(key=str.lower)
    files.sort(key=str.lower)
    return folders + files


# ================= THE MAIN TREE FUNCTION =================
# L1 step 4: function with depth
# L1 step 5: it calls itself (recursion)
# L2 step 9: prefix carries the | pieces down
def print_tree(folder, depth, prefix, counts, opt, ancestors):
    # L3 step 12: locked folder -> print message and carry on
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
        full_path = os.path.join(folder, name)   # L1 step 3: need the full path
        is_link = os.path.islink(full_path)      # L3 step 13

        # L2 step 9: last item gets └──, the rest get ├──
        if index == len(entries) - 1:
            connector = "└── "
            extension = "    "
        else:
            connector = "├── "
            extension = "│   "

        if os.path.isdir(full_path):
            counts[0] += 1                       # L1 step 6: folder count
            label = name + "/"
            # L4 item 16: folder size, looked up not recalculated
            if opt["sizes"] is not None and full_path in opt["sizes"]:
                label += "   " + format_size(opt["sizes"][full_path])
            # L3 step 13: mark symlinks
            if is_link:
                label += " -> " + os.readlink(full_path) + " [symlink]"
            print(prefix + connector + label)

            # L2 step 7: only go inside if depth limit allows
            if opt["max_depth"] is None or depth < opt["max_depth"]:
                real = os.path.realpath(full_path)
                # L3 step 13: symlink loop protection
                if real in ancestors:
                    print(prefix + extension + "└── [symlink loop skipped]")
                else:
                    # L4 item 19: ancestors is just the current path stack
                    ancestors.append(real)
                    print_tree(full_path, depth + 1, prefix + extension,
                               counts, opt, ancestors)
                    ancestors.pop()
        else:
            try:
                size = os.path.getsize(full_path)   # L2 step 10
            except OSError:
                size = 0
            counts[1] += 1                       # L1 step 6: file count
            counts[2] += size                    # L2 step 10: total bytes
            label = name
            if is_link:                          # L3 step 13
                label += " -> " + os.readlink(full_path) + " [symlink]"
            print(prefix + connector + label + "   " + format_size(size))


# ================= LEVEL 4 item 17: --summary (CSV) =================

# writes one CSV row per folder (after its children)
# and returns what the parent needs
def summarize(folder, rel, depth, writer, exclude):
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
        if is_excluded(name, exclude):          # item 20
            continue
        full_path = os.path.join(folder, name)
        if rel == ".":
            child_rel = name
        else:
            child_rel = os.path.join(rel, name)

        if os.path.isdir(full_path):
            if os.path.islink(full_path):       # item 13
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


# ================= LEVEL 4 item 18: --compare =================

# collects every file in a folder: {relative path: (size, mtime)}
def collect_files(folder, rel, found, exclude):
    try:
        names = os.listdir(folder)
    except OSError:
        return
    for name in names:
        if is_excluded(name, exclude):          # item 20
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


# compares A and B: only in A, only in B, changed (size first, then mtime)
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


# ================= MAIN PROGRAM: read the settings =================

# L2 steps 7 and 8, L3 step 14, L4 items 17 to 20: command line options
parser = argparse.ArgumentParser(description="Directory tree printer")
parser.add_argument("root", nargs="?")                       # L1 step 1: the folder
parser.add_argument("--max-depth", type=int, default=None)   # L2 step 7
parser.add_argument("--files", action=argparse.BooleanOptionalAction, default=True)  # L2 step 8
parser.add_argument("--ext", default="")                     # L3 step 14
parser.add_argument("--pattern", default="")                 # L3 step 14
parser.add_argument("--exclude", default="")                 # L4 item 20
parser.add_argument("--summary", action="store_true")        # L4 item 17
parser.add_argument("--compare", metavar="OTHER_FOLDER", default=None)  # L4 item 18
parser.add_argument("--stream", action="store_true")         # L4 item 19
args = parser.parse_args()

if args.root is None:
    # no options typed -> ask with prompts (the original input() style)
    root = input("Root folder: ")                            # L1 step 1
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
        depth_text = input("Max depth (Enter for no limit): ")   # L2 step 7
        if depth_text != "":
            try:                                                 # L3 step 11 bonus
                max_depth = int(depth_text)
            except ValueError:
                print("Error: max depth must be a whole number.")
                sys.exit(1)
        show_files = input("Show files (y/n): ").strip().lower() != "n"   # L2 step 8
        ext_text = input("Extensions e.g. .py,.json (Enter for all): ")   # L3 step 14
        pattern = input("Name pattern e.g. test_* (Enter for none): ")    # L3 step 14
        stream = input("Stream mode, no folder sizes (y/n, Enter = n): ").strip().lower() == "y"  # L4 item 19
else:
    # options typed on the command line
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

# ================= RUN THE CHOSEN MODE =================

check_folder(root)                       # L3 step 11

if mode == "summary":                    # L4 item 17
    writer = csv.writer(sys.stdout, lineterminator="\n")
    writer.writerow(["folder", "files", "total_bytes",
                     "largest_file", "largest_bytes", "deepest_path"])
    summarize(root, ".", 0, writer, exclude)

elif mode == "compare":                  # L4 item 18
    check_folder(other)
    compare_folders(root, other, exclude)

else:                                    # normal tree (Levels 1 to 3)
    sizes = None
    if not stream:                       # L4 item 16: sizes unless streaming
        sizes = {}
        compute_sizes(root, exclude, sizes)

    # all settings in one dictionary so print_tree stays tidy
    opt = {
        "max_depth": max_depth,
        "show_files": show_files,
        "exts": exts,
        "pattern": pattern,
        "exclude": exclude,
        "sizes": sizes,
    }

    counts = [0, 0, 0]                   # L1 step 6 + L2 step 10: [folders, files, bytes]
    shown = root.rstrip("/") or root
    header = shown + "/"
    if sizes is not None:
        header += "   " + format_size(sizes[root])
    print(header)
    print_tree(root, 0, "", counts, opt, [os.path.realpath(root)])   # L1 step 4: first call
    print(f"{counts[0]} folders, {counts[1]} files, total {format_size(counts[2])}")  # L1 step 6
