import os


# lists a folder and goes into every subfolder
def print_tree(folder, depth, counts):
    indent = "    " * depth  # 4 spaces per level

    # listdir only gives names, not full paths
    # and the order is random, sort it later (level 3)
    names = os.listdir(folder)

    for i in names:
        # need the full path or isdir looks in the wrong place
        full_path = os.path.join(folder, i)

        if os.path.isdir(full_path):
            counts[0] += 1
            print(indent + i + "/")
            # depth + 1, not a fixed number, or it breaks past level 1
            # full_path not i, same reason as above
            print_tree(full_path, depth + 1, counts)
        else:
            counts[1] += 1
            print(indent + i)
    # recursion stops by itself: empty folder = loop doesn't run


root = input("Root folder: ")

# [folders, files]
# a list because a plain number gets copied inside the function
# and the count would be lost
counts = [0, 0]

# no print() around this, the function already prints
# and it would show "None" at the end
print_tree(root, 0, counts)

print(f"{counts[0]} folders, {counts[1]} files")

# things I got wrong:
# - os.listdir(root) on its own does nothing, had to save it in a variable
# - used full_path before making it
# - passed depth 1 instead of depth + 1
# - ran mkdir in the wrong folder and got projects/projects
