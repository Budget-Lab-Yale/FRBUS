#!/bin/bash
#SBATCH --output dsq-jobx-%A_%3a-%N.out
#SBATCH --array 0-175
#SBATCH --job-name dsq-jobx
#SBATCH --mem-per-cpu 4g -t 60:00 --mail-type ALL

# DO NOT EDIT LINE BELOW
/vast/palmer/apps/avx2/software/dSQ/1.05/dSQBatch.py --job-file /gpfs/gibbs/project/sarin/jmk263/Repositories/FRBUS/general-testing/jobx.txt --suppress-stats-file

