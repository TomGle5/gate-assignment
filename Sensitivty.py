
import subprocess
import sys
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


# ============================================================
# SETTINGS
# ============================================================

PROJECT_FOLDER = Path(__file__).resolve().parent
MAIN_FILE = PROJECT_FOLDER / "main.py"

FIRST_AIRCRAFT_COUNT = 50
LAST_AIRCRAFT_COUNT = 150
AIRCRAFT_STEP = 10

NUMBER_OF_SEEDS = 10
FIRST_SEED = 42

# Only include solutions meeting this relative gap
MAX_ACCEPTED_GAP = 0.01

RAW_RESULTS_FILE = PROJECT_FOLDER / "Sensitivity_Raw.csv"
SUMMARY_FILE = PROJECT_FOLDER / "Sensitivity_Summary.csv"

WALKING_GRAPH = PROJECT_FOLDER / "Sensitivity_Walking.png"
APRON_GRAPH = PROJECT_FOLDER / "Sensitivity_Apron.png"
RUNTIME_GRAPH = PROJECT_FOLDER / "Sensitivity_Runtime.png"


# ============================================================
# RUN ONE SCENARIO
# ============================================================

def run_scenario(number_of_aircraft, seed):

    command = [sys.executable, str(MAIN_FILE), str(number_of_aircraft), str(seed)]

    # Generate Gantt chart only for the first seed of the largest aircraft scenario
    if (number_of_aircraft == LAST_AIRCRAFT_COUNT and seed == FIRST_SEED):
        command.append("--gantt")

    completed = subprocess.run(command, cwd=PROJECT_FOLDER, capture_output=True, text=True)

    if completed.returncode != 0:
        print(f"ERROR: {number_of_aircraft} aircraft, seed {seed}")
        
        print(completed.stderr[-2000:])

        return None

    for line in completed.stdout.splitlines():

        line = line.strip()

        if line.startswith("RESULT,"):

            fields = line.split(",")

            if len(fields) != 7:
                raise ValueError(f"Unexpected result format: {line}")

            reported_aircraft = int(fields[1])

            if reported_aircraft != number_of_aircraft:
                raise ValueError("Aircraft count mismatch")

            return {
                "Number of flights": number_of_aircraft,
                "Seed": seed,
                "Walking distance": float(fields[2]),
                "Apron usage": float(fields[3]),
                "Runtime": float(fields[4]),
                "MIP Gap": float(fields[5]),
                "Solver status": int(fields[6])}

        if line.startswith("NO_SOLUTION,"):
            print(f"No solution: {number_of_aircraft} aircraft, seed {seed}")
            
            return None

    print(f"WARNING: No result found for {number_of_aircraft}, seed {seed}")
    
    print(completed.stdout[-2000:])

    return None


# ============================================================
# PLOTTING
# ============================================================



def plot_sensitivity(data, raw_data, mean_column, min_column, max_column, raw_column, ylabel, title, filename):

    x = data["Number of flights"].to_numpy()
    mean = data[mean_column].to_numpy()
    lower = data[min_column].to_numpy()
    upper = data[max_column].to_numpy()

    plt.figure(figsize=(5.5, 5.5))

    # Mean value
    plt.plot(
        x,
        mean,
        marker="o",
        markersize=5,
        linewidth=2,
        color="tab:blue",
        label="Mean")

    # Shaded minimum-maximum range
    plt.fill_between(
        x,
        lower,
        upper,
        color="tab:blue",
        alpha=0.2,
        label="Minimum–maximum range")

    # Individual results for all 10 seeds
    plt.scatter(
        raw_data["Number of flights"],
        raw_data[raw_column],
        color="tab:blue",
        s=15,
        alpha=0.5,
        label="Individual seeds",
        zorder=3)

    plt.xlabel("Number of flights")
    plt.ylabel(ylabel)
    plt.title(title)

    plt.xlim(FIRST_AIRCRAFT_COUNT, LAST_AIRCRAFT_COUNT + 10)
    #plt.ylim(bottom=0)

    plt.grid(True, alpha=0.3)
    plt.legend()

    plt.gca().set_box_aspect(1)
    plt.tight_layout()

    plt.savefig(filename, dpi=300)
    plt.close()


# ============================================================
# MAIN SENSITIVITY ANALYSIS
# ============================================================

def main():

    if not MAIN_FILE.exists():
        raise FileNotFoundError(f"Could not find main.py: {MAIN_FILE}")

    aircraft_counts = range(FIRST_AIRCRAFT_COUNT, LAST_AIRCRAFT_COUNT + 1, AIRCRAFT_STEP)

    seeds = range(FIRST_SEED, FIRST_SEED + NUMBER_OF_SEEDS)

    total_runs = len(aircraft_counts) * NUMBER_OF_SEEDS

    results = []
    run_number = 0

    for number_of_aircraft in aircraft_counts:

        for seed in seeds:

            run_number += 1

            print(f"Run {run_number}/{total_runs}: {number_of_aircraft} aircraft, seed {seed}", flush=True)

            result = run_scenario(number_of_aircraft, seed)

            if result is not None:
                results.append(result)

    if not results:
        print("No results collected.")
        return

    # --------------------------------------------------------
    # SAVE ALL INDIVIDUAL RUNS
    # --------------------------------------------------------

    raw_data = pd.DataFrame(results)

    raw_data.to_csv(RAW_RESULTS_FILE, index=False)

    # Only accept solutions with sufficiently small MIP gap
    accepted_data = raw_data[raw_data["MIP Gap"] <= MAX_ACCEPTED_GAP].copy()

    if accepted_data.empty:
        print("No solutions met the MIP gap criterion.")
        return

    # --------------------------------------------------------
    # CALCULATE STATISTICS
    # --------------------------------------------------------

    summary = (accepted_data.groupby("Number of flights").agg(
        Mean_Walking=("Walking distance", "mean"),
        #Std_Walking=("Walking distance", "std"),
        Min_Walking=("Walking distance", "min"),
        Max_Walking=("Walking distance", "max"),

        Mean_Apron=("Apron usage", "mean"),
        #Std_Apron=("Apron usage", "std"),
        Min_Apron=("Apron usage", "min"),
        Max_Apron=("Apron usage", "max"),

        Mean_Runtime=("Runtime", "mean"),
        #Std_Runtime=("Runtime", "std"),
        Min_Runtime=("Runtime", "min"),
        Max_Runtime=("Runtime", "max"),

        Number_of_Runs=("Seed", "count")).reset_index())

    summary.to_csv(SUMMARY_FILE,index=False)

    # --------------------------------------------------------
    # WALKING DISTANCE + Axis Labels
    # --------------------------------------------------------

    plot_sensitivity(
        summary,
        accepted_data,
        "Mean_Walking",
        "Min_Walking",
        "Max_Walking",
        "Walking distance",
        "Walking distance per passenger [m]",
        "Objective Function for Number of Flights",
        WALKING_GRAPH)

    # --------------------------------------------------------
    # Apron % + Axis Labels
    # --------------------------------------------------------

    plot_sensitivity(
        summary,
        accepted_data,
        "Mean_Apron",
        "Min_Apron",
        "Max_Apron",
        "Apron usage",
        "Apron Fraction [%]",
        "Apron Allocation for Number of Flights",
        APRON_GRAPH)

    # --------------------------------------------------------
    # Runtime + Axis Labels
    # --------------------------------------------------------

    plot_sensitivity(
        summary,
        accepted_data,
        "Mean_Runtime",
        "Min_Runtime",
        "Max_Runtime",
        "Runtime",
        "Solver Runtime [s]",
        "Computational Effort for Number of Flights",
        RUNTIME_GRAPH)

    # --------------------------------------------------------
    # PRINT RESULTS
    # --------------------------------------------------------

    print("\nSensitivity analysis completed.")

    print("\nSummary statistics:")
    print(summary.to_string(index=False))

    print("\nFiles saved:")
    print(RAW_RESULTS_FILE)
    print(SUMMARY_FILE)
    print(WALKING_GRAPH)
    print(APRON_GRAPH)
    print(RUNTIME_GRAPH)

    expected = NUMBER_OF_SEEDS

    incomplete = summary[summary["Number_of_Runs"] < expected]

    if not incomplete.empty:
        print("\nWARNING: Some aircraft counts have fewer accepted runs than requested.")
        
        print(incomplete[["Number of flights", "Number_of_Runs"]].to_string(index=False))


if __name__ == "__main__":
    main()
