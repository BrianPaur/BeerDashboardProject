import os

def print_tree(start_path='.', prefix='', output_lines=None):
    if output_lines is None:
        output_lines = []
    items = sorted(os.listdir(start_path))
    for index, item in enumerate(items):
        path = os.path.join(start_path, item)
        connector = '└── ' if index == len(items) - 1 else '├── '
        output_lines.append(prefix + connector + item)
        if os.path.isdir(path) and item != '__pycache__':
            extension = '    ' if index == len(items) - 1 else '│   '
            print_tree(path, prefix + extension, output_lines)
    return output_lines

if __name__ == '__main__':
    tree_output = print_tree('.')
    with open('project_tree.txt', 'w', encoding='utf-8') as f:
        f.write("Project Directory Tree:\n\n")
        f.write('\n'.join(tree_output))
