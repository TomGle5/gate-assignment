import itertools
import math
import random
import csv
import sys
from gurobipy import *
from DistanceMatrix import dist

#random.seed(42)
n_aircraft = int(sys.argv[1]) if len(sys.argv) > 1 else 100
seed = int(sys.argv[2]) if len(sys.argv) > 2 else 42

random.seed(seed)

aircraft = list(range(1, n_aircraft + 1))

# SCHEDULES ======================================================================================
# Schedules (wave/bank structure)
# arrival = {i: random.randint(0, 90) for i in aircraft}
# turnaround = {i: random.randint(40, 60) for i in aircraft}
# departure = {i: random.randint(max((arrival[i] + turnaround[i]), 90), 180) for i in aircraft}
# aircraft_size = {i: random.choices(('wide', 'narrow'), (0.3, 0.7)) for i in aircraft}
# aircraft_zone = {i: random.choice(('schengen', 'non-schengen')) for i in aircraft}
# # Schedules (random) ===========================================================================

#this decedides the window of analysis [min] -> Lets assume 06:00 - 23:00 window
analysis_period = 1020
arrival = {i: random.randint(0, analysis_period) for i in aircraft}


#turnaround = {i: random.randint(30, 60) for i in aircraft}
aircraft_size = {i: random.choices(('wide', 'narrow'), (0.3, 0.7)) for i in aircraft}
turnaround = {i: (random.randint(60, 120)
    if aircraft_size[i] == ['wide']
    else random.randint(30, 60))
    for i in aircraft
}

departure = {i: arrival[i] + turnaround[i] for i in aircraft}
aircraft_zone = {i: random.choice(('schengen', 'non-schengen')) for i in aircraft}
remaining_capacity = {
    i: 300 if aircraft_size[i] == ['wide'] else 180
    for i in aircraft
}

aircraft, arrival, turnaround, departure, aircraft_size, aircraft_zone, remaining_capacity = multidict({
    i: [
        arrival[i],
        turnaround[i],
        departure[i],
        aircraft_size[i],
        aircraft_zone[i],
        remaining_capacity[i]
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

# distances between gates and E
D0g = {g: dist["E"][g] for g in gates}
Dg0 = {g: dist[g]["E"] for g in gates}
Dgg = {(g1, g2): dist[g1][g2] for g1 in gates for g2 in gates}

# # Pax flows
# P0i = {i: random.randint(50, 200) for i in aircraft}                    # check-in -> i
# Pi0 = {i: random.randint(50, 200) for i in aircraft}                    # i -> luggage
# Pij = {(i, j): random.randint(0, 50) for i in aircraft for j in aircraft if i != j}  # i -> j transfers

# Passenger flows
mct = 40  # minimum connecting time
P_arr = {}  # passengers arriving on each ac
cnx_pct_plan = {}  # 'planned' pct of arriving pax cnx to another flt
cnx_pax_arr_plan = {}  # 'planned' no of arr pax cnx to another flt
Pi0 = {}  # no of pax ending journey at the airport
cnx_pct_actual = {}  # actual pct of arriving pax cnx to another flt

A_sorted = sorted(aircraft, key=lambda i: arrival[i])  # ac sorted by arrival time

valid_connections = {  # flts that a pax can connect onto (departs after arriving flt + mct)
    i: [j for j in aircraft if departure[j] >= (arrival[i] + mct)]
    for i in aircraft
} 

for i in aircraft:
    if aircraft_size[i] == ['wide']:
        P_arr[i] = random.randint(100, 300)
        cnx_pct_plan[i] = random.randint(40, 80)/100
        cnx_pax_arr_plan[i] = math.floor(P_arr[i] * cnx_pct_plan[i])
        Pi0[i] = P_arr[i] - cnx_pax_arr_plan[i]
    elif aircraft_size[i] == ['narrow']:
        P_arr[i] = random.randint(50, 180)
        cnx_pct_plan[i] = random.randint(20, 70)/100
        cnx_pax_arr_plan[i] = math.floor(P_arr[i] * cnx_pct_plan[i])
        Pi0[i] = P_arr[i] - cnx_pax_arr_plan[i]

Pij = {(i, j): 0 for i in aircraft for j in aircraft}

def min_origin(j):
    return 100 if aircraft_size[j] == ['wide'] else 50

# Allocate planned connecting passengers to feasible departures. Earlier
# departures receive greater weight, while aircraft capacity is respected.
for i in A_sorted:
    candidates = [j for j in valid_connections[i] if remaining_capacity[j] > min_origin(j)]

    for _ in range(cnx_pax_arr_plan[i]):
        if not candidates:
            Pi0[i] += 1
            continue  
        weights = [1/(departure[j]-arrival[i]) for j in candidates]
        j  = random.choices(candidates, weights=weights, k=1)[0]
        Pij[(i, j)] += 1
        remaining_capacity[j] -= 1
        candidates = [c for c in candidates if remaining_capacity[c] > min_origin(c)]


# for i in aircraft:
#     for _ in range(cnx_pax_arr[i]):
#         j = random.choice(aircraft)
#         Pij[(i, j)] += 1

cnx_pax_dep = {  # total pax per dep ac who have cnx'd from another flt
    j: sum(Pij[(i, j)] for i in aircraft)
    for j in aircraft
}

cnx_pax_arr_actual = {  # total pax per arr ac who cnx to another flt
    i: sum(Pij[(i, j)] for j in aircraft)
    for i in aircraft
}

cnx_pct_actual = {i: cnx_pax_arr_actual[i]/P_arr[i] for i in aircraft}

P0i = {}
for i in aircraft:
    if aircraft_size[i] == ['wide']:
        P0i[i] = random.randint(100, 300 - cnx_pax_dep[i])
    elif aircraft_size[i] == ['narrow']:
        P0i[i] = random.randint(50, 180 - cnx_pax_dep[i])

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
    for i, j in transfer_pairs
    for g1 in G_i[i] for g2 in G_i[j]
)

model.setObjective(outbound + inbound + transfer, GRB.MINIMIZE)

# ----------------------------------------------------------------------
# 8. Solve and report
# ----------------------------------------------------------------------
model.optimize()

#added for senitivity abnalysis
if model.SolCount > 0:

    total_passengers = (
        sum(P0i.values())
        + sum(Pi0.values())
        + sum(Pij.values())
    )

    objective_per_passenger = (
        model.ObjVal / total_passengers
        if total_passengers > 0 else 0
    )

    print(
        f"RESULT,{n_aircraft},{objective_per_passenger}"
    )

else:
    print(f"NO_SOLUTION,{n_aircraft}")



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
from matplotlib.patches import Patch

# def plot_gantt(A, G, x, arrival, departure):
#     fig, ax = plt.subplots(figsize=(12, 6))
    
#     # Colour per gate (apron gets grey)
#     colours = plt.cm.tab20.colors
#     #gate_colours = {g: 'lightgrey' if g == 0 else colours[g % len(colours)] for g in G}
#     gate_colours = {g: 'lightgrey' if g == "R" else colours[idx % len(colours)] 
#                 for idx, g in enumerate(G)}
#     ac_colours = {('wide', 'non-schengen'): 'blue',
#                   ('narrow', 'non-schengen'): 'red',
#                   ('wide', 'schengen'): 'orange',
#                   ('narrow', 'schengen'): 'green'}
#     #ac_cat_tuple = (aircraft_size[i][0], aircraft_zone[i] for i in aircraft)
#     # Draw a bar for each aircraft assignment
    
#     for g in G:
#         for i in A:
#             ac_cat_tuple = (aircraft_size[i][0], aircraft_zone[i])
#             if x[i, g].X > 0.5:
#                 label = "Apron" if g == "R" else f"Gate {g}"
#                 ax.barh(
#                     y=label,
#                     width=departure[i] - arrival[i],
#                     left=arrival[i],
#                     color=ac_colours[ac_cat_tuple],
#                     edgecolor='black',
#                     linewidth=0.8,
#                     alpha=0.85
#                 )
#                 # Label each bar with the aircraft number
#                 mid = arrival[i] + (departure[i] - arrival[i]) / 2
#                 ax.text(
#                     mid,
#                     label,
#                     f"AC{i}",
#                     ha='center',
#                     va='center',
#                     fontsize=8,
#                     fontweight='bold'
#                 )
    
#     ax.set_xlabel("Time (minutes)")
#     ax.set_title("Gate Assignment Gantt Chart")
#     ax.set_xlim(0, max(departure.values()) + 10)
#     ax.grid(axis='x', linestyle='--', alpha=0.5)
#     legend_labels = {
#     ('wide', 'non-schengen'): 'Wide-body, Non-Schengen',
#     ('narrow', 'non-schengen'): 'Narrow-body, Non-Schengen',
#     ('wide', 'schengen'): 'Wide-body, Schengen',
#     ('narrow', 'schengen'): 'Narrow-body, Schengen'}
#     legend_handles = [
#         Patch(facecolor=color, edgecolor='black', label=legend_labels[cat])
#         for cat, color in ac_colours.items()
#     ]

#     ax.legend(handles=legend_handles, title="Aircraft Category", loc='upper right', bbox_to_anchor=(1.15, 1))
#     plt.tight_layout()
#     #plt.savefig("gantt.png", dpi=150)
#     plt.show()
def plot_gantt(A, G, x, arrival, departure):
    fig, ax = plt.subplots(figsize=(14, 6))

    colours = plt.cm.tab20.colors
    gate_colours = {g: 'lightgrey' if g == "R" else colours[idx % len(colours)]
                     for idx, g in enumerate(G)}
    ac_colours = {('wide', 'non-schengen'): 'blue',
                  ('narrow', 'non-schengen'): 'red',
                  ('wide', 'schengen'): 'orange',
                  ('narrow', 'schengen'): 'green'}

    # --- Step 1: figure out how many sub-rows the apron needs ---
    apron_aircraft = sorted(
        [i for i in A if x[i, "R"].X > 0.5],
        key=lambda i: arrival[i]
    )

    apron_row_end = []  # tracks the departure time currently occupying each apron row
    apron_row_of = {}   # aircraft -> row index (0, 1, 2, ...)

    for i in apron_aircraft:
        placed = False
        for row_idx, end_time in enumerate(apron_row_end):
            if arrival[i] >= end_time:
                apron_row_end[row_idx] = departure[i]
                apron_row_of[i] = row_idx
                placed = True
                break
        if not placed:
            apron_row_end.append(departure[i])
            apron_row_of[i] = len(apron_row_end) - 1

    n_apron_rows = len(apron_row_end)

    # --- Step 2: build y-axis labels/order: apron sub-rows first, then gates ---
    apron_labels = [f"Apron {r+1}" for r in range(n_apron_rows)] if n_apron_rows else ["Apron"]
    gate_labels = [f"Gate {g}" for g in G if g != "R"]
    y_order = apron_labels + gate_labels
    ax.set_yticks(range(len(y_order)))
    ax.set_yticklabels(y_order)
    y_pos = {label: pos for pos, label in enumerate(y_order)}

    # --- Step 3: draw bars ---
    for g in G:
        for i in A:
            if x[i, g].X <= 0.5:
                continue
            ac_cat_tuple = (aircraft_size[i][0], aircraft_zone[i])

            if g == "R":
                label = f"Apron {apron_row_of[i] + 1}"
            else:
                label = f"Gate {g}"

            width = departure[i] - arrival[i]
            ax.barh(
                y=y_pos[label],
                width=width,
                left=arrival[i],
                color=ac_colours[ac_cat_tuple],
                edgecolor='black',
                linewidth=0.8,
                alpha=0.85
            )

            mid = arrival[i] + width / 2
            # only draw label if bar is wide enough to fit text legibly
            if width > (max(departure.values()) * 0.015):
                ax.text(
                    mid, y_pos[label], f"AC{i}",
                    ha='center', va='center',
                    fontsize=7, fontweight='bold', color='white'
                )

    ax.set_xlabel("Time (minutes)")
    ax.set_title("Gate Assignment Gantt Chart")
    ax.set_xlim(0, max(departure.values()) + 10)
    ax.grid(axis='x', linestyle='--', alpha=0.5)

    from matplotlib.patches import Patch
    legend_labels = {
        ('wide', 'non-schengen'): 'Wide-body, Non-Schengen',
        ('narrow', 'non-schengen'): 'Narrow-body, Non-Schengen',
        ('wide', 'schengen'): 'Wide-body, Schengen',
        ('narrow', 'schengen'): 'Narrow-body, Schengen',
    }
    legend_handles = [
        Patch(facecolor=color, edgecolor='black', label=legend_labels[cat])
        for cat, color in ac_colours.items()
    ]
    ax.legend(handles=legend_handles, title="Aircraft Category",
              loc='upper left', bbox_to_anchor=(1.01, 1))

    plt.tight_layout(rect=[0, 0, 0.85, 1])
    #plt.show()

# Call after model.optimize()
for i in aircraft:
    print(i, aircraft_size[i], aircraft_zone[i])

for i in aircraft:
    for j in aircraft:
        print(i, j, Pij[(i,j)])

print(f"{'i':<3} {'Size':<10} {'Zone':<10} {'Arrival':<10} {'Turnaround':<10} {'Departure':<10}")
print("-" * 100)

for i in aircraft:
    #print(i, aircraft_size[i][0][0], aircraft_zone[i][0], arrival[i], turnaround[i], departure[i], P_arr[i])
    print(f"{i:<3} {aircraft_size[i][0][0]:<10} {aircraft_zone[i][0]:<10} {arrival[i]:<10} {turnaround[i]:<10} {departure[i]:<10}")

print(f"{'i':<3} {'P_arr':<10} {'cnx_pct_plan':<20} {'cnx_pax_arr_plan':<20} {'Pi0':<5} {'cnx_pax_arr_plan + Pi0'}")
print("-" * 100)
for i in aircraft:
    print(f"{i:<3} {P_arr[i]:<10} {cnx_pct_plan[i]:<20} {cnx_pax_arr_plan[i]:<20} {Pi0[i]:<5} {cnx_pax_arr_plan[i]+Pi0[i]}")

print(f"{'i':<3} {'P_arr':<10} {'cnx_pct_actual':<20} {'cnx_pax_arr_actual':<20} {'Pi0':<5} {'cnx_pax_arr_actual + Pi0'}")
print("-" * 100)
for i in aircraft:
    print(f"{i:<3} {P_arr[i]:<10} {round(cnx_pct_actual[i], 2):<20} {cnx_pax_arr_actual[i]:<20} {Pi0[i]:<5} {cnx_pax_arr_actual[i]+Pi0[i]}")

print(f"{'i':<3} {'P0i':<10} {'cnx_pax_dep':<20} {'P0i + cnx_pax_dep'}")
print("-" * 100)
for i in aircraft:
    print(f"{i:<3} {P0i[i]:<10} {cnx_pax_dep[i]:<20} {P0i[i] + cnx_pax_dep[i]}")

# Get sorted unique row (i) and column (j) values
rows = sorted(set(i for i, j in Pij))
cols = sorted(set(j for i, j in Pij))

with open('Pij.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    # Header row with column labels
    writer.writerow([''] + cols)
    for i in rows:
        writer.writerow([i] + [Pij.get((i, j), '') for j in cols])

plot_gantt(aircraft, gates, x, arrival, departure)
