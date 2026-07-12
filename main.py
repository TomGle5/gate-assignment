from gurobipy import *
import random
import itertools
from DistanceMatrix import dist

random.seed(42)
n_gates = 24
n_aircraft = 40
aircraft = list(range(1, n_aircraft + 1))

# Schedules
arrival = {i: random.randint(0, 120) for i in aircraft}
turnaround = {i: random.randint(20, 40) for i in aircraft}
departure = {i: arrival[i] + turnaround[i] for i in aircraft}
aircraft_size = {i: random.choices(('wide', 'narrow'), (0.3, 0.7)) for i in aircraft}
aircraft_zone = {i: random.choice(('schengen', 'non-schengen')) for i in aircraft}

aircraft, arrival, turnaround, departure, aircraft_size, aircraft_zone = multidict({
    i: [
        arrival[i],
        turnaround[i],
        departure[i],
        aircraft_size[i],
        aircraft_zone[i]
    ]
    for i in aircraft
})

# (start, end, size, zone) - end inclusive
gate_ranges = [
    (1, 5,  'wide',   'non-schengen'),
    (6, 10,  'narrow', 'non-schengen'),
    (11, 15, 'narrow', 'schengen'),
    (16, 17, 'wide',  'schengen'),
    (18, 22, 'narrow', 'schengen')
#    ('R', 'R', 'wide', 'remote')
]

gate_data = {
    i: (zone, size)
    for start, end, size, zone in gate_ranges
    for i in range(start, end + 1)
}

gate_data['R'] = ('remote', 'wide')


gates, gate_zone, gate_size = multidict(gate_data)

# # Temporary walking distances
# D0g = {g: random.randint(300, 500) if g == 0 else random.randint(50, 300) for g in gates}
# Dg0 = {g: random.randint(300, 500) if g == 0 else random.randint(50, 300) for g in gates}
# Dgg = {(g1, g2): 0 if g1 == g2
#        else (random.randint(300, 500) if (g1 == 0 or g2 == 0) else random.randint(50, 300))
#        for g1 in gates for g2 in gates}

D0g = {g: dist["E"][g] for g in gates}
Dg0 = {g: dist[g]["E"] for g in gates}
Dgg = {(g1, g2): dist[g1][g2] for g1 in gates for g2 in gates}

# Pax flows
P0i = {i: random.randint(50, 200) for i in aircraft}                    # check-in -> i
Pi0 = {i: random.randint(50, 200) for i in aircraft}                    # i -> luggage
Pij = {(i, j): random.randint(0, 50) for i in aircraft for j in aircraft if i != j}  # i -> j transfers

# Create G_i
G_i = {i: [] for i in aircraft}
for i in aircraft:
    for g in gates:
        if gate_zone[g] == aircraft_zone[i]:
            if aircraft_size[i] == ['wide'] and gate_size[g] == 'wide':
                G_i[i].append(g)
            elif aircraft_size[i] == ['narrow']:
                G_i[i].append(g)
        if gate_zone[g] == 'remote':
            G_i[i].append(g)

# for i in aircraft:
#     print(i, aircraft_size[i], aircraft_zone[i], G_i[i])

# A_inc time incompatibility sets
A_sorted = sorted(aircraft, key=lambda i: arrival[i])
A_inc = {i: [] for i in aircraft}
for idx, i in enumerate(A_sorted):
    for j in A_sorted[:idx]:
        if departure[j] >= arrival[i]:
            A_inc[i].append(j)

# Build model
model = Model('GAP')

x = model.addVars(aircraft, gates, vtype=GRB.BINARY, name='x')

# (2) each aircraft assigned to exactly one allowed gate
for i in aircraft:
    model.addConstr(quicksum(x[i,g] for g in G_i[i]) == 1, name=f'assign_{i}')

# (3) time-incompatible aircraft cannot share a physical gate (apron excluded)
for i in aircraft:
    for j in A_inc[i]:
        common_gates = (set(G_i[i]) & set(G_i[j])) - {"R"}
#        common_gates = (set(G_i[i]) & set(G_i[j])) 
        for g in common_gates:
            model.addConstr(x[i, g] + x[j, g] <= 1, name=f"incompat_{i}_{j}_{g}")

# # (4)-(6) linearization variables for transfer-passenger term
# y = {}
# for i, j in itertools.combinations(aircraft, 2):
#     for g1 in G_i[i]:
#         for g2 in G_i[j]:
#             y[i, g1, j, g2] = model.addVar(vtype=GRB.BINARY, name=f"y_{i}_{g1}_{j}_{g2}")
#             model.addConstr(y[i, g1, j, g2] >= x[i, g1] + x[j, g2] - 1)
#             model.addConstr(y[i, g1, j, g2] <= x[i, g1])
#             model.addConstr(y[i, g1, j, g2] <= x[j, g2])
# Only iterate over pairs with actual transfer flow
transfer_pairs = [(i, j) for i, j in itertools.combinations(aircraft, 2)
                  if Pij.get((i,j), 0) + Pij.get((j,i), 0) > 0]

y = {}
for i, j in transfer_pairs:
    for g1 in G_i[i]:
        for g2 in G_i[j]:
            y[i, g1, j, g2] = model.addVar(vtype=GRB.BINARY, name=f"y_{i}_{g1}_{j}_{g2}")
            model.addConstr(y[i, g1, j, g2] >= x[i, g1] + x[j, g2] - 1)
            model.addConstr(y[i, g1, j, g2] <= x[i, g1])
            model.addConstr(y[i, g1, j, g2] <= x[j, g2])

for i, j in transfer_pairs:
    for g1 in G_i[i]:
        model.addConstr(
            quicksum(y[i, g1, j, g2] for g2 in G_i[j]) == x[i, g1],
            name=f"agg1_{i}_{g1}_{j}"
        )
    for g2 in G_i[j]:
        model.addConstr(
            quicksum(y[i, g1, j, g2] for g1 in G_i[i]) == x[j, g2],
            name=f"agg2_{i}_{j}_{g2}"
        )


# ----------------------------------------------------------------------
# 7. Objective (eq. 1)
# ----------------------------------------------------------------------
outbound = quicksum(P0i[i] * D0g[g] * x[i, g] for i in aircraft for g in G_i[i])
inbound = quicksum(Pi0[i] * Dg0[g] * x[i, g] for i in aircraft for g in G_i[i])
transfer = quicksum(
    (Pij.get((i, j), 0) + Pij.get((j, i), 0)) * Dgg[g1, g2] * y[i, g1, j, g2]
    for i, j in itertools.combinations(aircraft, 2)
    for g1 in G_i[i] for g2 in G_i[j]
)

model.setObjective(outbound + inbound + transfer, GRB.MINIMIZE)

# ----------------------------------------------------------------------
# 8. Solve and report
# ----------------------------------------------------------------------
model.optimize()

print("\nSchedules:")
for i in aircraft:
    print(f"  Aircraft {i}: A_i={arrival[i]:3d}  D_i={departure[i]:3d}")

print("\nGate assignments:")
for i in aircraft:
    for g in gates:
        if x[i, g].X > 0.5:
            label = "APRON" if g == "R" else f"Gate {g}"
            print(f"  Aircraft {i} -> {label}")

print(f"\nTotal objective (passenger walking distance): {model.ObjVal:.1f}")

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

def plot_gantt(A, G, x, arrival, departure, n_gates):
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Colour per gate (apron gets grey)
    colours = plt.cm.tab20.colors
    #gate_colours = {g: 'lightgrey' if g == 0 else colours[g % len(colours)] for g in G}
    gate_colours = {g: 'lightgrey' if g == "R" else colours[idx % len(colours)] 
                for idx, g in enumerate(G)}
    # Draw a bar for each aircraft assignment
    for i in A:
        for g in G:
            if x[i, g].X > 0.5:
                label = "Apron" if g == "R" else f"Gate {g}"
                ax.barh(
                    y=label,
                    width=departure[i] - arrival[i],
                    left=arrival[i],
                    color=gate_colours[g],
                    edgecolor='black',
                    linewidth=0.8,
                    alpha=0.85
                )
                # Label each bar with the aircraft number
                mid = arrival[i] + (departure[i] - arrival[i]) / 2
                ax.text(
                    mid,
                    label,
                    f"AC{i}",
                    ha='center',
                    va='center',
                    fontsize=8,
                    fontweight='bold'
                )
    
    ax.set_xlabel("Time (minutes)")
    ax.set_title("Gate Assignment Gantt Chart")
    ax.set_xlim(0, max(departure.values()) + 10)
    ax.grid(axis='x', linestyle='--', alpha=0.5)
    plt.tight_layout()
    plt.savefig("gantt.png", dpi=150)
    plt.show()

# Call after model.optimize()
plot_gantt(aircraft, gates, x, arrival, departure, n_gates)           