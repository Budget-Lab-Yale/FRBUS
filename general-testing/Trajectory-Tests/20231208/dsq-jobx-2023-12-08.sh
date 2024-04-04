#!/bin/bash
#SBATCH --output dsq-jobx-%A_%2a-%N.out
#SBATCH --array 0-43
#SBATCH --job-name dsq-jobx
#SBATCH --mem-per-cpu 4g -t 20:00 --mail-type ALL --partition scavenge

# DO NOT EDIT LINE BELOW
/vast/palmer/apps/avx2/software/dSQ/1.05/dSQBatch.py --job-file /gpfs/gibbs/project/sarin/jmk263/Repositories/FRBUS/general-testing/Trajectory-Tests/20231208/jobx.txt --status-dir /gpfs/gibbs/project/sarin/jmk263/Repositories/FRBUS/general-testing/Trajectory-Tests/20231208

