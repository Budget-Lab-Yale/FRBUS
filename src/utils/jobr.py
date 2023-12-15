import numpy

rates = numpy.array([0,1,2,5])
count = 0

f = open('/gpfs/gibbs/project/sarin/jmk263/Repositories/FRBUS/general-testing/jobx.txt', 'w')

for y in numpy.arange(start=10, stop=21):
    for i in rates:
        line = "module load miniconda; conda activate ybl-frbus; "
        f.write(line)
        for j in rates:
            line = f"python3 traj_test_cmd.py {y} {i} {j} {count}; "
            f.writelines(line)
            count +=1
        line = "\n"
        f.write(line)
f.close()
