# Default values
nprocs=44

module load compiler-rt/2024.0.0 ifort/2024.0.0 mpi/2021.13

mkdir -p ./log

fname="test-2_xyz_raw"

mpirun -np $nprocs ../../bin/./waveqlab3d ./input/${fname}.in | tee ./log/${fname}.log
    