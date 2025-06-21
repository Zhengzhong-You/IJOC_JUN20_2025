#!/bin/bash
#SBATCH --job-name=tally_open_instance
#SBATCH -p hpg-default
#SBATCH --qos=yu.yang1
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=16GB
#SBATCH -t 3-23:00:00
#SBATCH --output=tally_open_instance.out
#SBATCH --error=tally_open_instance.err

module load gcc
module load gurobi/10.0.0

python3 tally_open_instance.py X-n384-k52
python3 tally_open_instance.py X-n313-k71
python3 tally_open_instance.py X-n359-k29
