# !/usr/bin/env python3
import os
import re
import json
import shutil
import threading
import argparse
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# Global locks and flags for thread-safe operations.
tree_lock = threading.Lock()
optimal_copy_lock = threading.Lock()
root_copy_lock = threading.Lock()
optimal_copied = False
root_copied = False
overall_time = 0
overall_nodes = 0


class Node:
    def __init__(self, branch=None, relation=None, parent=None):
        """
        Initializes a node in the binary tree.
        :param branch: The branch info (e.g., "49-105") that this node represents.
        :param relation: Relationship to its parent ('left' or 'right').
        :param parent: Pointer to the parent node.
        """
        self.branch = branch  # The branch info extracted from the file.
        self.relation = relation  # 'left' (for '-') or 'right' (for '+').
        self.parent = parent  # Pointer to parent node.
        self.left = None  # Left child (for '-' directive).
        self.right = None  # Right child (for '+' directive).
        self.occupied = False  # Marked as True only when the final brc in a segment is processed.

    def to_dict(self):
        # Return a dictionary representation for JSON dumping.
        return {
            "branch": self.branch,
            "relation": self.relation,
            "occupied": self.occupied,
            "left": self.left.to_dict() if self.left else None,
            "right": self.right.to_dict() if self.right else None,
        }


# The global tree root. Its branch and relation are None.
tree_root = Node()


def insert_group(branch_group):
    """
    Insert a contiguous branch group (i.e., a sequence of (branch_str, direction) tuples)
    into the tree. For every tuple in the group:
      - If the parent's corresponding child (by direction) does not exist, create it
        and mark it as unoccupied.
      - If it already exists, check that its branch info matches; if not, return False to
        signal a conflict and skip processing this file.
    After the entire group is processed, mark the final node as occupied.
    :param branch_group: List of tuples (branch_str, direction).
    :return: True if inserted successfully, False if conflict encountered.
    """
    global tree_root
    current = tree_root
    for branch_str, direction in branch_group:
        with tree_lock:
            if direction == '-':
                if current.left is None:
                    new_node = Node(branch=branch_str, relation='left', parent=current)
                    current.left = new_node
                    current = new_node
                else:
                    if current.left.branch != branch_str:
                        # Conflict: The existing left child does not match the branch info.
                        return False
                    current = current.left
            elif direction == '+':
                if current.right is None:
                    new_node = Node(branch=branch_str, relation='right', parent=current)
                    current.right = new_node
                    current = new_node
                else:
                    if current.right.branch != branch_str:
                        # Conflict: The existing right child does not match the branch info.
                        return False
                    current = current.right
            else:
                # Unexpected direction.
                return False
    # Mark the final node in this branch group as occupied (if not already).
    with tree_lock:
        if not current.occupied:
            current.occupied = True
    return True


def process_file(file_path, instance_folder, instance_id):
    """
    Process an individual file by:
      - Checking for the key phrase "Updated UB:" and copying the file as
        optimal_<instance_id>.txt if found.
      - Checking for "idx= 0 value= 0 enu= 0" and copying the file as
        root_<instance_id>.txt if found.
      - Reading all lines and splitting the file into contiguous branch segments,
        where each line matching the pattern "brc= <num>-<num> : [+-]" belongs to a segment.
      - For each segment, insert the branch path into the global binary tree.
      - If at any point a parent already has a child with different branch info,
        skip processing this file.
    """
    global optimal_copied, root_copied
    try:
        with open(file_path, 'r', encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return

    content = "".join(lines)
    # tally the time used;
    # <Elapsed Time= 981.8>
    # seach for the pattern; and add to the overall_time;
    pattern = r"<Elapsed Time=\s*(\d+(?:\.\d+)?)>"
    # <Nodes Explored= 23>
    pattern_nodes = r"<Nodes Explored=\s*(\d+)>"
    match = re.search(pattern, content)
    match2 = re.search(pattern_nodes, content)
    if match and match2:
        time_used = float(match.group(1))
        nodes_used = int(match2.group(1))
        global overall_time
        global overall_nodes
        overall_nodes += nodes_used
        overall_time += time_used
        # print(f"overall_time: {overall_time}")
    else:
        return

    # Check for the keywords and copy the file if necessary.
    if "Updated UB:" in content:
        with optimal_copy_lock:
            if not optimal_copied:
                dest_fname = f"optimal_{instance_id}.txt"
                dest_path = os.path.join(instance_id, dest_fname)
                try:
                    shutil.copy(file_path, dest_path)
                    print(f"Copied optimal file to {dest_path}")
                    optimal_copied = True
                except Exception as e:
                    print(f"Error copying {file_path} to {dest_path}: {e}")
    if "idx= 0 value= 0 enu= 0" in content:
        with root_copy_lock:
            if not root_copied:
                dest_fname = f"root_{instance_id}.txt"
                dest_path = os.path.join(instance_id, dest_fname)
                try:
                    shutil.copy(file_path, dest_path)
                    print(f"Copied root file to {dest_path}")
                    root_copied = True
                except Exception as e:
                    print(f"Error copying {file_path} to {dest_path}: {e}")

    # Process branch segments.
    # The pattern matches lines like: "brc= 49-105 : -" or "brc= 12-76 : +"
    pattern = r"brc=\s*(\d+\-\d+)\s*:\s*([+-])"
    branch_groups = []
    current_group = []

    # Split file into segments based on contiguous matching lines.
    for line in lines:
        line = line.strip()
        match = re.search(pattern, line)
        if match:
            branch_str = match.group(1)
            direction = match.group(2)
            current_group.append((branch_str, direction))
        else:
            if current_group:
                branch_groups.append(current_group)
                current_group = []
    if current_group:
        branch_groups.append(current_group)

    # For each branch group found in the file, insert it into the tree.
    for group in branch_groups:
        if not group:
            continue
        if not insert_group(group):
            return
            # print(f"Skipping file {file_path} due to branch conflict in group: {group}")
        else:
            return  # Skip processing this file entirely if conflict encountered.


def report_empty_leaf_nodes(node, path=None, results=None):
    """
    Recursively traverse the tree to collect paths for nodes that
    are leaves (no children) and are not marked as occupied.
    :param node: The current node.
    :param path: List of branch strings (with relation info) from root to current node.
    :param results: A list to collect empty branch paths.
    :return: List of paths (each path is a list of node info) for empty leaves.
    """
    if path is None:
        path = []
    if results is None:
        results = []
    if node.branch is not None:
        # Format the branch with its relation.
        path = path + [f"{node.branch}({node.relation})"]
    if node.left is None and node.right is None:
        if not node.occupied:
            results.append(path)
    else:
        if node.left:
            report_empty_leaf_nodes(node.left, path, results)
        if node.right:
            report_empty_leaf_nodes(node.right, path, results)
    return results


def write_tree_to_file(filename):
    """
    Write the global tree to a JSON file.
    The JSON structure is compact and can be reloaded later.
    """
    try:
        with open(filename, 'w', encoding="utf-8") as f:
            json.dump(tree_root.to_dict(), f)
        print(f"Tree written to {filename}")
    except Exception as e:
        print(f"Error writing tree to {filename}: {e}")


def main(instance_folder, threads=256):
    instance_id = instance_folder

    instance_folder = f"{instance_folder}/cvrp_open_{instance_id}_out"

    if not os.path.isdir(instance_folder):
        print(f"Error: {instance_folder} is not a valid directory.")
        return

    beg_time = time.time()
    file_list = []
    with os.scandir(instance_folder) as it:
        for entry in it:
            if entry.is_file():
                file_list.append(entry.path)
    print(f"Found {len(file_list)} files to process.")

    end_time = time.time()
    print(f"Time taken to list files with os.scandir: {end_time - beg_time:.2f} seconds.")

    # exit(0)

    # Process files concurrently.
    with ThreadPoolExecutor(max_workers=threads) as executor:
        futures = [executor.submit(process_file, file_path, instance_folder, instance_id)
                   for file_path in file_list]
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                print(f"An error occurred during file processing: {e}")

    # After processing, report any empty leaf nodes (i.e. branches not marked as occupied).
    empty_leaves = report_empty_leaf_nodes(tree_root)
    if empty_leaves:
        print("Empty branch(es) (leaf nodes not marked as occupied):")
        for branch_path in empty_leaves:
            print(" -> ".join(branch_path))
    else:
        print("All branch leaves are occupied.")

    # Write the final tree structure out to a JSON file.
    tree_file = os.path.join(instance_id, f"tree_{instance_id}.json")
    write_tree_to_file(tree_file)

    end_time = time.time()
    print(f"Total time taken: {end_time - beg_time:.2f} seconds.")
    print(f"Overall time used: {overall_time:.2f} seconds.")
    print(f"Overall nodes explored: {overall_nodes}.")


if __name__ == '__main__':
    # Get the instance name from the command line
    argparser = argparse.ArgumentParser()
    argparser.add_argument("instance_name", type=str, nargs='?', help="Instance name from command line")
    args = argparser.parse_args()

    main(args.instance_name)
