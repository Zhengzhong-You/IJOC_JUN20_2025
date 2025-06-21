# !/usr/bin/env python3
import os
import re


def parse_tally_file(filepath="tally_open_instance.out"):
    """
    Read the tally file and build a mapping:
       instance_name -> { overall_time_used, overall_nodes_explored }
    """
    instance_data = {}
    current_instance = None
    with open(filepath, "r") as f:
        for line in f:
            # Look for the optimal file line to get the instance name.
            if "Copied optimal file to" in line:
                # Expected format: "Copied optimal file to X-n384-k52/optimal_X-n384-k52.txt"
                m = re.search(r"Copied optimal file to\s+(\S+)/optimal_", line)
                if m:
                    current_instance = m.group(1)
                    instance_data[current_instance] = {}
            elif "Overall time used:" in line and current_instance:
                m = re.search(r"Overall time used:\s*([\d\.]+)", line)
                if m:
                    instance_data[current_instance]["overall_time_used"] = float(m.group(1))
            elif "Overall nodes explored:" in line and current_instance:
                m = re.search(r"Overall nodes explored:\s*(\d+)", line)
                if m:
                    instance_data[current_instance]["overall_nodes_explored"] = int(m.group(1))
    return instance_data


def parse_optimal_file(instance_folder):
    """
    For a given instance folder (e.g., "X-n384-k52"), open the optimal file,
    scan until a line containing "Updated UB:" and count lines that begin with "brc=".
    Count the total number of branches, left branches (with '-') and right branches (with '+').
    """
    optimal_path = os.path.join(instance_folder, f"optimal_{instance_folder}.txt")
    total_branches = 0
    left_branches = 0
    right_branches = 0
    with open(optimal_path, "r") as f:
        for line in f:
            if "Updated UB:" in line:
                break
            if line.strip().startswith("brc="):
                total_branches += 1
                # After the colon, the branch sign should be the last character (either '+' or '-')
                sign = line.strip()[-1]
                if sign == '+':
                    right_branches += 1
                elif sign == '-':
                    left_branches += 1
            if line.strip().startswith("idx="):
                total_branches = 0
                left_branches = 0
                right_branches = 0
    return total_branches, left_branches, right_branches


def parse_root_file(instance_folder):
    """
    For a given instance folder (e.g., "X-n384-k52"), open the root file
    and read until the substring "we directly test" is encountered.
    Record the last occurrence (before that point) of:
      - "elapsed time=" (as root_time),
      - "lpval=" and "ub=" (in the same line).
    """
    root_path = os.path.join(instance_folder, f"root_{instance_folder}.txt")
    root_time = None
    lpval = None
    ub = None
    with open(root_path, "r") as f:
        for line in f:
            if "we directly test" in line:
                break
            # Update root_time if present
            if "elapsed time=" in line:
                m_time = re.search(r"elapsed time=\s*([\d\.]+)", line)
                if m_time:
                    root_time = float(m_time.group(1))
            # Look for a line with both lpval and ub values.
            if "lpval=" in line and "ub=" in line:
                m_gap = re.search(r"lpval=\s*([\d\.]+)\s+ub=\s*([\d\.]+)", line)
                if m_gap:
                    lpval = float(m_gap.group(1))
                    ub = float(m_gap.group(2))
    return root_time, lpval, ub


def generate_latex_table(instances_info):
    """
    Given a dictionary of instance metrics, return a LaTeX table as a string.
    Column meanings:
      - Instance: folder name
      - Root/s: root elapsed time (seconds)
      - Root Gap/%: computed gap in percentage
      - CPU/y: overall time used converted from seconds to years
      - #Nodes: overall nodes explored converted to millions
      - Total Branches, Left Branches, Right Branches: branch counts
    """
    header = r"""\begin{table}[htbp]
\centering
\small
\caption{Metrics for Challenging CVRP Instances}
\label{table:open instance}
\begin{tabular}{lcccc|ccc}
\hline
Instance & Root/s & Root Gap/\% & CPU/y & \#Nodes/10^6 & Total Branches & Left Branches & Right Branches \\
\hline
"""
    footer = r"\hline" + "\n" + r"\end{tabular}" + "\n" + r"\end{table}"
    rows = ""
    # sort instances by name
    instances_info = dict(sorted(instances_info.items()))
    for instance, info in instances_info.items():
        # Compute root gap percentage if lpval is positive.
        if info["lpval"] and info["lpval"] != 0:
            root_gap = (info["ub"] - info["lpval"]) / info["ub"] * 100
        else:
            root_gap = 0.0
        # Convert overall time (seconds) to years.
        cpu_year = info["overall_time_used"] / 31536000.0  # 31536000 seconds in one year
        # Convert overall nodes to millions.
        nodes_millions = info["overall_nodes_explored"] / 1e6
        # Format the row.
        row = f"{instance} & {info['root_time']:.2f} & {root_gap:.2f}\\% & {cpu_year:.2f} & {nodes_millions:.2f} & {info['total_branches']} & {info['left_branches']} & {info['right_branches']} \\\\\n"
        rows += row
    return header + rows + footer


def main():
    # Parse the tally file.
    tally_filepath = "tally_open_instance.out"
    overall_map = parse_tally_file(tally_filepath)
    if not overall_map:
        print("No instance data found in", tally_filepath)
        return

    instances_info = {}
    for instance in overall_map.keys():
        # Parse the optimal file.
        try:
            total_br, left_br, right_br = parse_optimal_file(instance)
        except Exception as e:
            print(f"Error processing optimal file for {instance}: {e}")
            total_br, left_br, right_br = (0, 0, 0)
        # Parse the root file.
        try:
            root_time, lpval, ub = parse_root_file(instance)
        except Exception as e:
            print(f"Error processing root file for {instance}: {e}")
            root_time, lpval, ub = (0.0, 0.0, 0.0)
        # Gather all metrics.
        overall_time_used = overall_map[instance].get("overall_time_used", 0.0)
        overall_nodes_explored = overall_map[instance].get("overall_nodes_explored", 0)
        instances_info[instance] = {
            "overall_time_used": overall_time_used,
            "overall_nodes_explored": overall_nodes_explored,
            "root_time": root_time if root_time is not None else 0.0,
            "lpval": lpval if lpval is not None else 0.0,
            "ub": ub if ub is not None else 0.0,
            "total_branches": total_br,
            "left_branches": left_br,
            "right_branches": right_br
        }

    # Generate the LaTeX table.
    latex_table = generate_latex_table(instances_info)
    print(latex_table)

    # Optionally, write the table to a file.
    with open("metrics_table.tex", "w") as f:
        f.write(latex_table)
    print("LaTeX table written to metrics_table.tex")


if __name__ == '__main__':
    main()
