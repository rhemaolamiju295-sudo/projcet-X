import os


def print_tree(folder, depth):
    indent = "    " * depth
    names = os.listdir(folder)
    for i in names:
        full_path = os.path.join(folder, i)

        if os.path.isdir(full_path):
            print(indent + i + "/")
            print_tree(full_path, depth + 1)

        else:
            print(indent + i)

root =  input("Root folder: ")
print_tree(root, 0)
