from gurobipy import *
import numpy as np
import random
import itertools

random.seed(42)
n_aircraft = 10
n_gates = 4
aircraft = list(range(1, n_aircraft + 1))
#G = list(range(0, n_gates + 1))

#G_i = {i: G for i in A}

# Schedules
arrival = {i: random.randint(0, 100) for i in aircraft}
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
    (1, 4,  'wide',   'non-schengen'),
    (5, 8,  'narrow', 'non-schengen'),
    (9, 16, 'narrow', 'schengen'),
    (17, 20, 'wide',  'schengen'),
]

gate_data = {
    f'G{i}': (zone, size)
    for start, end, size, zone in gate_ranges
    for i in range(start, end + 1)
}

gates, gate_zone, gate_size = multidict(gate_data)

# Temporary walking distances
D0g = {g: random.randint(300, 500) if g == 0 else random.randint(50, 300) for g in gates}
Dg0 = {g: random.randint(300, 500) if g == 0 else random.randint(50, 300) for g in gates}
Dgg = {(g1, g2): 0 if g1 == g2
       else (random.randint(300, 500) if (g1 == 0 or g2 == 0) else random.randint(50, 300))
       for g1 in gates for g2 in gates}

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

A_sorted = sorted(aircraft, key=lambda i: arrival[i])
A_inc = {i: [] for i in aircraft}
for idx, i in enumerate(A_sorted):
    for j in A_sorted[:idx]:
        if departure[j] >= arrival[i]:
            A_inc[i].append(j)

