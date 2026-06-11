"""
Minimal simulation of the basic Gate Assignment Problem (GAP)
following AE4446 Lecture 4 (slides 18-27).

Sets:
    A  = aircraft, indexed 1..n
    G  = gates, indexed 0..m   (gate 0 = apron, infinite capacity)

Decision variables:
    x[i,g]      = 1 if aircraft i is assigned to gate g
    y[i,g1,j,g2]= 1 if i->g1 AND j->g2 (linearization for transfer term)

Objective: minimize total passenger walking distance
    (outbound + inbound + transfer passengers)
"""

import itertools
import random
import gurobipy as gp
from gurobipy import GRB

random.seed(42)

# ----------------------------------------------------------------------
# 1. Sets
# ----------------------------------------------------------------------
n_aircraft = 6
n_gates = 3                       # physical gates 1..n_gates
A = list(range(1, n_aircraft + 1))
G = list(range(0, n_gates + 1))   # 0 = apron (infinite capacity)

# Each aircraft can use any gate (incl. apron) -> G_i
G_i = {i: G for i in A}

# ----------------------------------------------------------------------
# 2. Schedules (A_i = arrival, D_i = departure)
# ----------------------------------------------------------------------
arrival = {i: random.randint(0, 100) for i in A}
turnaround = {i: random.randint(20, 40) for i in A}
departure = {i: arrival[i] + turnaround[i] for i in A}

# ----------------------------------------------------------------------
# 3. Walking-distance parameters
# ----------------------------------------------------------------------
# Apron (gate 0) is deliberately the worst option: passengers need a bus,
# so its "walking" distance is set higher than any normal gate distance.
D0g = {g: random.randint(300, 500) if g == 0 else random.randint(50, 300) for g in G}
Dg0 = {g: random.randint(300, 500) if g == 0 else random.randint(50, 300) for g in G}
Dgg = {(g1, g2): 0 if g1 == g2
       else (random.randint(300, 500) if (g1 == 0 or g2 == 0) else random.randint(50, 300))
       for g1 in G for g2 in G}

# ----------------------------------------------------------------------
# 4. Passenger flows
# ----------------------------------------------------------------------
P0i = {i: random.randint(50, 200) for i in A}                    # check-in -> i
Pi0 = {i: random.randint(50, 200) for i in A}                    # i -> luggage
Pij = {(i, j): random.randint(0, 50) for i in A for j in A if i != j}  # i -> j transfers

# ----------------------------------------------------------------------
# 5. Time-incompatibility sets A_inc^i  (aircraft sorted by arrival)
# ----------------------------------------------------------------------
A_sorted = sorted(A, key=lambda i: arrival[i])
A_inc = {i: [] for i in A}
for idx, i in enumerate(A_sorted):
    for j in A_sorted[:idx]:
        if departure[j] >= arrival[i]:
            A_inc[i].append(j)

# ----------------------------------------------------------------------
# 6. Build the model
# ----------------------------------------------------------------------
model = gp.Model("GAP_basic")

x = model.addVars(A, G, vtype=GRB.BINARY, name="x")

# (2) each aircraft assigned to exactly one allowed gate
for i in A:
    model.addConstr(gp.quicksum(x[i, g] for g in G_i[i]) == 1, name=f"assign_{i}")

# (3) time-incompatible aircraft cannot share a physical gate (apron excluded)
for i in A:
    for j in A_inc[i]:
        common_gates = (set(G_i[i]) & set(G_i[j])) - {0}
        for g in common_gates:
            model.addConstr(x[i, g] + x[j, g] <= 1, name=f"incompat_{i}_{j}_{g}")

# (4)-(6) linearization variables for transfer-passenger term
y = {}
for i, j in itertools.combinations(A, 2):
    for g1 in G_i[i]:
        for g2 in G_i[j]:
            y[i, g1, j, g2] = model.addVar(vtype=GRB.BINARY, name=f"y_{i}_{g1}_{j}_{g2}")
            model.addConstr(y[i, g1, j, g2] >= x[i, g1] + x[j, g2] - 1)
            model.addConstr(y[i, g1, j, g2] <= x[i, g1])
            model.addConstr(y[i, g1, j, g2] <= x[j, g2])

# ----------------------------------------------------------------------
# 7. Objective (eq. 1)
# ----------------------------------------------------------------------
outbound = gp.quicksum(P0i[i] * D0g[g] * x[i, g] for i in A for g in G_i[i])
inbound = gp.quicksum(Pi0[i] * Dg0[g] * x[i, g] for i in A for g in G_i[i])
transfer = gp.quicksum(
    (Pij.get((i, j), 0) + Pij.get((j, i), 0)) * Dgg[g1, g2] * y[i, g1, j, g2]
    for i, j in itertools.combinations(A, 2)
    for g1 in G_i[i] for g2 in G_i[j]
)

model.setObjective(outbound + inbound + transfer, GRB.MINIMIZE)

# ----------------------------------------------------------------------
# 8. Solve and report
# ----------------------------------------------------------------------
model.optimize()

print("\nSchedules:")
for i in A:
    print(f"  Aircraft {i}: A_i={arrival[i]:3d}  D_i={departure[i]:3d}")

print("\nGate assignments:")
for i in A:
    for g in G:
        if x[i, g].X > 0.5:
            label = "APRON" if g == 0 else f"Gate {g}"
            print(f"  Aircraft {i} -> {label}")

print(f"\nTotal objective (passenger walking distance): {model.ObjVal:.1f}")