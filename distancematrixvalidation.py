# Variable from Excel cell C30
d = 2000

# Distance matrix
# Nodes: E, 1, 2, ..., 22, R

nodes = [
    "E", 1, 2, 3, 4, "R"
]

distance_matrix = [
    #E,     1,   2,   3,   4,   R 
    [0,   125, 125, 125, 125, 500], #E
    [125,   0,  50, 250, 250, 625], #1
    [125,  50,   0, 250, 250, 625], #2
    [125, 250, 250,   0,  50, 625], #3
    [125, 250, 250,  50,   0, 625], #4
    [500, 625, 625, 625, 625, 1250]  #R
]
# easier retrieval
dist = {
    nodes[i]: {
        nodes[j]: distance_matrix[i][j]
        for j in range(len(nodes))
    }
    for i in range(len(nodes))
}

# Example:
#print(dist["E"]["R"])   # gives 420+d