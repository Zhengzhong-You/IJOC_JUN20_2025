import os
import re
import math


def get_instance_group(instance_name):
    """
    Determine the group for an instance based on its name.
    If the instance name contains an underscore, it belongs to group "HG",
    otherwise it is classified as "Solomon".
    """
    if "_" in instance_name:
        return "HG"
    else:
        return "Solomon"


def getLineGroup(instance_name):
    """ we have C, R, RC"""
    if "RC" in instance_name:
        return "RC"
    elif "R" in instance_name:
        return "R"
    elif "C" in instance_name:
        return "C"
    else:
        return "Unknown"


def process_routeopt_file(filepath):
    """
    Process a RouteOpt .txt file.

    It extracts:
      - Instance name (from the file name)
      - UB, LB, overall elapsed time, and nodes from the summary block.
      - Global gap (0 if LB==UB; otherwise, (1 - LB/UB)*100) and optimal flag.
      - Root information: root time and lpval (to compute root gap as (1 - lpval/UB)*100)
        from lines containing "elapsed time=" and "lpval=" until a line with "we directly test" is encountered.
    """
    result = {}
    instance_name = os.path.splitext(os.path.basename(filepath))[0]
    if '_' in instance_name:
        # Optionally adjust the instance name if needed.
        instance_name = instance_name.split('_')
        instance_name = '\_'.join(instance_name[2:])

    result['instance'] = instance_name

    UB = None
    LB = None
    cpu_time = None
    nodes = None

    with open(filepath, 'r') as f:
        lines = f.readlines()

    # Extract overall values from the file (from the block with <UB= ...> etc.)
    for line in lines:
        if UB is None:
            m = re.search(r"<UB=\s*([\d.]+)>", line)
            if m:
                UB = float(m.group(1))
        if LB is None:
            m = re.search(r"<LB=\s*([\d.]+)>", line)
            if m:
                LB = float(m.group(1))
        if cpu_time is None:
            m = re.search(r"<Elapsed Time=\s*([\d.]+)>", line)
            if m:
                cpu_time = min(float(m.group(1)), 3600.0)
        if nodes is None:
            m = re.search(r"<Nodes Explored=\s*(\d+)>", line)
            if m:
                nodes = int(m.group(1))

    # Compute global gap and optimal flag
    if UB is not None and LB is not None:
        if abs(UB - LB) < 1e-6:  # LB equals UB (within tolerance)
            gap = 0.0
            opt = 1
        else:
            gap = (1 - (LB / UB)) * 100
            opt = 0
    else:
        gap = None
        opt = None

    # Extract root information from lines up to "we directly test"
    root_time = None
    lpval = None
    for line in lines:
        if "we directly test" in line:
            break
        m = re.search(r"lpval=\s*([\d.]+)", line)
        if m:
            lpval = float(m.group(1))
        m = re.search(r"elapsed time=\s*([\d.]+)", line)
        if m:
            root_time = float(m.group(1))

    # Compute root gap if possible (using lpval/UB)
    if lpval is not None and UB is not None:
        root_gap = (1 - (lpval / UB)) * 100
    else:
        root_gap = None

    if nodes == 1:
        root_gap = gap
        root_time = cpu_time

    result.update({
        'opt': opt,
        'root_time': root_time if root_time is not None else cpu_time,
        'root_gap': root_gap if root_gap is not None else gap,
        'cpu_time': cpu_time,
        'nodes': nodes,
        'gap': gap
    })
    return result


def process_vrpsolver_file(filepath):
    """
    Process a VRPSolver .txt file.

    It looks for a statistics line with the following order:
      instance, :Optimal, cutoff, :bcRecRootDb, :bcTimeRootEval, :bcCountNodeProc, :bcRecBestDb, :bcRecBestInc, :bcTimeMain

    Then:
      - overall gap is computed as (1 - (bcRecBestDb / cutoff))*100.
      - Default root values are set to:
            root_time = overall CPU time (bcTimeMain)
            root_gap = overall gap.
      - If the file contains "Strong branching phase 1 is", then it re-reads the file to update:
            root_time: from the last occurrence of "<et=" before that marker.
            root_gap: computed as (1 - (Mlp / cutoff))*100 from the last occurrence of "<Mlp=".
    """
    result = {}
    instance_name = os.path.splitext(os.path.basename(filepath))[0]
    if '_' in instance_name:
        # Optionally adjust the instance name if needed.
        instance_name = instance_name.split('_')
        instance_name = '\_'.join(instance_name)

    with open(filepath, 'r') as f:
        lines = f.readlines()

    for line in lines:
        if "Best lower bound" in line:
            lb = float(line.split(":")[1].strip())
        if "Total time" in line:
            cpu_time = float(line.split(":")[1].strip().split()[0])
        if "Number of B&B nodes" in line:
            nodes = int(line.split(":")[1].strip())
        if "Root lower bound" in line:
            root_lb = float(line.split(":")[1].strip())
        if "Root time" in line:
            root_cpu = float(line.split(":")[1].strip().split()[0])
        if "<PB=" in line:
            # Pattern match for <PB=1401>
            cutoff = re.search(r"<PB=\s*([\d.]+)>", line)
            if cutoff:
                cutoff = float(cutoff.group(1))

    overall_gap = (1 - (lb / cutoff)) * 100
    root_cpu = min(root_cpu, 3600)  # Ensure root time does not exceed overall CPU time

    # Default: use overall CPU time and overall gap for root values.
    cpu_time = min(cpu_time, 3600.0)
    root_gap = (1 - (root_lb / cutoff)) * 100
    if root_gap < 1e-6:
        root_gap = 0
    if overall_gap < 1e-6:
        overall_gap = 0
    overall_opt = 1 if overall_gap == 0 else 0

    result.update({
        'instance': instance_name,
        'opt': overall_opt,
        'root_time': root_cpu,
        'root_gap': root_gap,
        'cpu_time': cpu_time,
        'nodes': nodes,
        'gap': overall_gap
    })

    return result


def geometric_mean(values):
    """Compute the geometric mean of a list of positive values."""
    if not values:
        return None
    return math.exp(sum(math.log(v) for v in values) / len(values))


def average(values):
    """Compute the arithmetic mean of a list of numbers."""
    if not values:
        return None
    return sum(values) / len(values)


def aggregate_data(data_list):
    """
    Group the list of instance dictionaries by instance group (HG/Solomon)
    and compute aggregated statistics:
      - "#Opt": count of optimal instances over total instances
      - "Root/s": geometric mean of root times
      - "Root Gap": average of root gaps
      - "CPU/s": geometric mean of CPU times
      - "#Nodes": geometric mean of nodes
      - "Gap": average of gaps
    """
    groups = {}
    for data in data_list:
        group = get_instance_group(data.get('instance'))
        groups.setdefault(group, []).append(data)

    aggregates = {}
    for group, items in groups.items():
        total = len(items)
        opt_count = sum(item['opt'] for item in items if item['opt'] is not None)
        root_times = [item['root_time'] for item in items if item['root_time'] is not None]
        cpu_times = [item['cpu_time'] for item in items if item['cpu_time'] is not None]
        nodes_list = [item['nodes'] for item in items if item['nodes'] is not None]
        root_gaps = [item['root_gap'] for item in items if item['root_gap'] is not None]
        gaps = [item['gap'] for item in items if item['gap'] is not None]

        aggregates[group] = {
            "#Opt": f"{opt_count}/{total}",
            "Root/s": geometric_mean(root_times) if root_times else None,
            "Root Gap": average(root_gaps) if root_gaps else None,
            "CPU/s": geometric_mean(cpu_times) if cpu_times else None,
            "#Nodes": geometric_mean(nodes_list) if nodes_list else None,
            "Gap": average(gaps) if gaps else None
        }
    return aggregates


def format_value(val, precision=1):
    if val is None:
        return "N/A"
    return f"{val:.{precision}f}"


def generate_latex_instance_table(routeopt_data, vrpsolver_data):
    """
    Create a LaTeX table that lists each shared instance (sorted by instance name)
    along with its individual statistics from both RouteOpt and VRPSolver.
    Instances are grouped by their group (HG if '_' in instance name, Solomon otherwise).
    Columns include:
       Instance, RouteOpt opt, RouteOpt root/s, RouteOpt root gap, RouteOpt CPU/s, RouteOpt #Nodes, RouteOpt gap,
       VRPSolver opt, VRPSolver root/s, VRPSolver root gap, VRPSolver CPU/s, VRPSolver #Nodes, VRPSolver gap.
    """
    # Build maps keyed by instance name.
    routeopt_map = {d.get('instance', 'Unknown'): d for d in routeopt_data}
    vrpsolver_map = {d.get('instance', 'Unknown'): d for d in vrpsolver_data}
    routeopt_map.pop('Unknown', None)
    vrpsolver_map.pop('Unknown', None)

    # Get the union of instance names.
    instance_names = sorted(
        list(set(routeopt_map.keys()).union(set(vrpsolver_map.keys())))
    )

    # 自定义排序函数：
    def sort_key(name):
        # 1. 根据组，Solomon 排在 HG 前面
        group_order = 0 if get_instance_group(name) == "Solomon" else 1
        # 2. 提取字母前缀（例如 "C", "R", "RC"）
        m = re.match(r"([A-Za-z]+)", name)
        letter_prefix = m.group(1) if m else ""
        # 3. 提取数字部分，并转为整数元组
        numeric_parts = tuple(int(x) for x in re.findall(r"\d+", name))
        return (group_order, letter_prefix, numeric_parts)

    instance_names.sort(key=sort_key)

    # # Sort by the trailing number if available.
    # def trailing_number(name):
    #     m = re.search(r"(\d+)$", name)
    #     return int(m.group(1)) if m else 0
    #
    # instance_names.sort(key=trailing_number)

    table = []
    table.append(r"\begin{table}[htbp]")
    table.append(r"\scriptsize")
    table.append(r"\centering")
    table.append(r"\caption{Performance of CVRPTW for RouteOpt and VRPSolver}")
    table.append(r"\label{tab_performance_comparison_cvrptw}")
    table.append(r"\begin{tabular}{lcccccccccccc}")
    table.append(r"\toprule")
    table.append(r"Instance & \multicolumn{6}{c}{RouteOpt} & \multicolumn{6}{c}{VRPSolver} \\")
    table.append(r"\cmidrule(lr){2-7}\cmidrule(lr){8-13}")
    table.append(
        r"         & Opt & Root/s & Root Gap/\% & CPU/s & \#Nodes & Gap/\% & Opt & Root/s & Root Gap/\% & CPU/s & \#Nodes & Gap/\% \\")
    table.append(r"\midrule")

    # Add instance-level rows (all instances are shown)
    current_group = getLineGroup(instance_names[0])
    for name in instance_names:
        group = getLineGroup(name)
        if group != current_group:
            table.append(r"\midrule")
            current_group = group
        ro = routeopt_map.get(name, {})
        vrp = vrpsolver_map.get(name, {})
        if ro.get('cpu_time') < 60 and vrp.get('cpu_time') < 60:
            continue
        row = f"{name} & "
        # RouteOpt data
        row += f"{ro.get('opt', 'N/A')} & {format_value(ro.get('root_time'))} & {format_value(ro.get('root_gap'), 2)} & {format_value(ro.get('cpu_time'))} & {format_value(ro.get('nodes'), 0)} & {format_value(ro.get('gap'), 2)} & "
        # VRPSolver data
        row += f"{vrp.get('opt', 'N/A')} & {format_value(vrp.get('root_time'))} & {format_value(vrp.get('root_gap'), 2)} & {format_value(vrp.get('cpu_time'))} & {format_value(vrp.get('nodes'), 0)} & {format_value(vrp.get('gap'), 2)} \\\\"
        table.append(row)

    table.append(r"\bottomrule")

    # --- Filtering for aggregate tallies ---
    # Exclude instances where both RouteOpt and VRPSolver CPU times are less than 60 seconds.
    filtered_names = []
    for name in instance_names:
        ro_time = routeopt_map.get(name, {}).get('cpu_time', math.inf)
        vrp_time = vrpsolver_map.get(name, {}).get('cpu_time', math.inf)
        # Only exclude if the instance exists in both and both times are < 60 seconds.
        if (name in routeopt_map and name in vrpsolver_map) and (ro_time < 60 and vrp_time < 60):
            continue
        filtered_names.append(name)

    # Build filtered data lists for aggregates.
    filtered_routeopt_data = [data for data in routeopt_data if data['instance'] in filtered_names]
    filtered_vrpsolver_data = [data for data in vrpsolver_data if data['instance'] in filtered_names]
    # --- End filtering for aggregates ---

    # Aggregate data by instance group (HG/Solomon) over the filtered instances.
    routeopt_aggregates = aggregate_data(filtered_routeopt_data)
    vrpsolver_aggregates = aggregate_data(filtered_vrpsolver_data)
    groups = sorted(set(routeopt_aggregates.keys()).union(vrpsolver_aggregates.keys()))

    groups.sort(key=lambda g: (0 if g == "Solomon" else 1, g))
    for group in groups:
        ro = routeopt_aggregates.get(group, {})
        vrp = vrpsolver_aggregates.get(group, {})
        row = f"{group} & "
        row += f"{ro.get('#Opt', 'N/A')} & {format_value(ro.get('Root/s'))} & {format_value(ro.get('Root Gap'), 2)} & {format_value(ro.get('CPU/s'))} & {format_value(ro.get('#Nodes'), 1)} & {format_value(ro.get('Gap'), 2)} & "
        row += f"{vrp.get('#Opt', 'N/A')} & {format_value(vrp.get('Root/s'))} & {format_value(vrp.get('Root Gap'), 2)} & {format_value(vrp.get('CPU/s'))} & {format_value(vrp.get('#Nodes'), 1)} & {format_value(vrp.get('Gap'), 2)} \\\\"
        table.append(row)
    table.append(r"\bottomrule")
    table.append(r"\end{tabular}")
    table.append(r"\end{table}")
    return "\n".join(table)


def pass_file(filename):
    # You can add additional logic to filter files if needed.
    return False


def main():
    routeopt_folder = "vrptw/RouteOpt"
    vrpsolver_folder = "vrptw/VRPSolver"

    routeopt_data = []
    vrpsolver_data = []

    # Process files from RouteOpt folder
    if os.path.isdir(routeopt_folder):
        for filename in os.listdir(routeopt_folder):
            if filename.endswith(".txt"):
                filepath = os.path.join(routeopt_folder, filename)
                if pass_file(filename):
                    continue
                try:
                    data = process_routeopt_file(filepath)
                    routeopt_data.append(data)
                except Exception as e:
                    print(f"Error processing {filepath}: {e}")
    else:
        print(f"Folder '{routeopt_folder}' does not exist.")

    # Process files from VRPSolver folder
    if os.path.isdir(vrpsolver_folder):
        for filename in os.listdir(vrpsolver_folder):
            if filename.endswith(".txt"):
                filepath = os.path.join(vrpsolver_folder, filename)
                if pass_file(filename):
                    continue
                try:
                    data = process_vrpsolver_file(filepath)
                    vrpsolver_data.append(data)
                except Exception as e:
                    print(f"Error processing {filepath}: {e}")
    else:
        print(f"Folder '{vrpsolver_folder}' does not exist.")

    # Generate and print the instance-level LaTeX table
    instance_table = generate_latex_instance_table(routeopt_data, vrpsolver_data)
    print("%% Instance-level Table")
    print(instance_table)
    print("\n")


if __name__ == "__main__":
    main()
