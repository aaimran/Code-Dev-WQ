#!/bin/bash
#SBATCH -J WaveQLab3D        # Job name
#SBATCH -o waveqlab3d.%j.out # Output file (%j is job ID)
#SBATCH -e waveqlab3d.%j.err # Error file
#SBATCH -t 48:00:00          # Time limit
#SBATCH -N 40                # Number of nodes
#SBATCH -n 5120              # Number of tasks (MPI processes)
#SBATCH -p normal            # Queue (partition)
#SBATCH --mail-type=ALL      # Mail events (NONE, BEGIN, END, FAIL, ALL)
#SBATCH --mail-user=@miners.utep.edu   # Email notifications



# Load necessary modules
module purge
module load intel/19.1.1
module load impi/19.0.9

mkdir -p ./output

#-------------------- 
CASE_NAME="test-2"
ibrun ../../build/./waveqlab3d ${CASE_NAME}.in > ./output/${CASE_NAME}.out
