#!/bin/bash
#
#SBATCH --job-name=$NAME
#SBATCH --mem=50000 # memory pool for all cores
#SBATCH --time=72:00:00 # time
#SBATCH -o TEM_logs/$NAME.%N.%j.out # STDOUT
#SBATCH -e TEM_logs/$NAME.%N.%j.err # STDERR
#SBATCH -p gpu
#SBATCH --gres=gpu:1
#SBATCH --ntasks=1

# Set the job name variable
NAME="TEM_big_50K"

source ~/.bashrc

conda activate NPG-env

python whittington_2020_run.py

exit