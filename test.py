import random
from gurobipy import *
import math

n_aircraft = 5
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

P_arr = {}
cnx_pct = {}
cnx_pax_arr = {}
Pi0 = {}
for i in aircraft:
    if aircraft_size[i] == ['wide']:
        P_arr[i] = random.randint(100, 300)
        cnx_pct[i] = random.randint(40, 80)/100
        cnx_pax_arr[i] = math.floor(P_arr[i] * cnx_pct[i])
        Pi0[i] = P_arr[i] - cnx_pax_arr[i]
    elif aircraft_size[i] == ['narrow']:
        P_arr[i] = random.randint(50, 180)
        cnx_pct[i] = random.randint(20, 70)/100
        cnx_pax_arr[i] = math.floor(P_arr[i] * cnx_pct[i])
        Pi0[i] = P_arr[i] - cnx_pax_arr[i]

# Pij = {}
# for i in aircraft:
#     for j in aircraft:
#         Pij[(i, j)] = random.randint(0, cnx_pax_arr[i])
#         cnx_pax_arr[i] = cnx_pax_arr[i] - Pij[(i, j)]

Pij = {(i, j): 0 for i in aircraft for j in aircraft}

for i in aircraft:
    for _ in range(cnx_pax_arr[i]):
        j = random.choice(aircraft)
        Pij[(i, j)] += 1

connecting_arrivals = {
    j: sum(Pij[(i, j)] for i in aircraft)
    for j in aircraft
}

P0i = {}
for i in aircraft:
    if aircraft_size[i] == ['wide']:
        P0i[i] = random.randint(100, 300 - connecting_arrivals[i])
    elif aircraft_size[i] == ['narrow']:
        P0i[i] = random.randint(50, 180 - connecting_arrivals[i])

print(aircraft_size)
print('================')
print(P_arr)
print('================')
print(cnx_pax_arr)
print('================')
print(Pi0)
print('================')
print(Pij)
print('================')
print(P0i)