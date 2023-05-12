import multiprocessing as mp
from time import sleep
import random


def test_function(value, val):
    sleep(random.random() * 2)
    print(value)
    val.value = value


if __name__ == '__main__':
    processes = []
    for i in range(5):
        val = mp.Value('i', 0)
        p = mp.Process(target=test_function, args=(i, val))
        processes.append((p, val))
        p.start()

    for p, val in processes:
        p.join()

    for p, val in processes:
        print(val.value)
