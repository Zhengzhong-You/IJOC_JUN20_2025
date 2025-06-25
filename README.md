
# RouteOpt: An Open-Source Modular Exact Solver for Vehicle Routing Problems

This repository provides the source code and data supporting our paper:

**RouteOpt: An Open-Source Modular Exact Solver for Vehicle Routing Problems**

RouteOpt is a flexible, modular solver designed for solving various Vehicle Routing Problems (VRPs). All necessary code, scripts, and datasets to replicate the results presented in the paper are included here.

## Contents

* **Code**: Source files and scripts for implementing and running RouteOpt.
* **Data**: Datasets for testing and validating the solver.
* **Documentation**: Instructions for reproducing experimental results.

## Generating Latex Tables

To generate LaTeX tables used in the paper, please run the following scripts from the `data` folder:

```bash
cd data
python get_cvrp.py
python get_vrptw.py
python get_open_table.py
````

These scripts will create the LaTeX tables presented in our article.

If you would like to run experiments on your own, please visit our main repository and follow the instructions under the **Getting Started** section:

* [https://github.com/Zhengzhong-You/RouteOpt](https://github.com/Zhengzhong-You/RouteOpt)

Currently, this repository serves primarily as a static snapshot of our code and data. User-friendly scripts for easy experiment execution will be provided shortly after paper revision.

## Citation

If you use RouteOpt in your research, please cite our paper accordingly.

```
```
