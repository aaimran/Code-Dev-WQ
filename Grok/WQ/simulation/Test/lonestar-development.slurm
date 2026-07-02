#!/bin/bash
#SBATCH -J WaveQLab3D        # Job name
#SBATCH -o waveqlab3d.%j.out # Output file (%j is job ID)
#SBATCH -e waveqlab3d.%j.err # Error file
#SBATCH -t 02:00:00          # Time limit
#SBATCH -N 8                # Number of nodes
#SBATCH -n 1024              # Number of tasks (MPI processes)
#SBATCH -p development            # Queue (partition)
#SBATCH --mail-type=ALL      # Mail events (NONE, BEGIN, END, FAIL, ALL)
#SBATCH --mail-user=@miners.utep.edu   # Email notifications



# Load necessary modules
module purge
module load intel/19.1.1
module load impi/19.0.9

mkdir -p ./output

#-------------------- 
CASE_NAME="test-2t"
ibrun ../../build/./waveqlab3d ${CASE_NAME}.in > ./output/${CASE_NAME}.out



