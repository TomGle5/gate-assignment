from gurobipy import *
import numpy as np

gates = []
for i in range(1, 11):
    gates.append(f'g_{i}')

aircraft  = {}


