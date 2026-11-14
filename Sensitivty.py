"""
Sensitivity.py

Runs main.py for aircraft counts 30 through 130 (inclusive), collects the
objective value per passenger movement, and saves:
    - Sensitivity_Results.csv
    - Sensitivity_Analysis.png

Run this file from your Python IDE (e.g. Spyder, PyCharm, VS Code, IDLE).
No terminal commands are required.

IMPORTANT:
main.py must:
  1. Read the aircraft count from sys.argv[1].
  2. Read the random seed from sys.argv[2] (optional, but recommended).
  3. Print one machine-readable line after optimisation:
       RESULT,n_aircraft,objective_per_passenger
     Example:
       RESULT,30,1245.6789

See the instructions accompanying this file for the small main.py changes.
"""

import subprocess
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


# ---------------------------------------------------------------------
# SETTINGS
# ---------------------------------------------------------------------

# Assumes Sensitivity.py and main.py are in the same folder.
PROJECT_FOLDER = Path(__file__).resolve().parent
MAIN_FILE = PROJECT_FOLDER / "main.py"

FIRST_AIRCRAFT_COUNT = 50
LAST_AIRCRAFT_COUNT = 100
RANDOM_SEED = 42

RESULTS_FILE = PROJECT_FOLDER / "Sensitivity_Results.csv"
GRAPH_FILE = PROJECT_FOLDER / "Sensitivity_Analysis.png"


# ---------------------------------------------------------------------
# RUN ONE SCENARIO
# ---------------------------------------------------------------------

def run_scenario(number_of_aircraft, seed=RANDOM_SEED):
    """
    Runs main.py as a separate Python process and returns the objective
    value per passenger movement.

    main.py must print:
        RESULT,n_aircraft,objective_per_passenger

    Returns None if the model has no feasible solution or no result line
    was printed.
    """

    command = [
        sys.executable,
        str(MAIN_FILE),
        str(number_of_aircraft),
        str(seed),
    ]

    completed = subprocess.run(
        command,
        cwd=PROJECT_FOLDER,
        capture_output=True,
        text=True
    )

    if completed.returncode != 0:
        print(f"ERROR: main.py failed for {number_of_aircraft} aircraft.")
        print(completed.stderr)
        return None

    # Look for the machine-readable RESULT line in main.py's output.
    for line in completed.stdout.splitlines():
        line = line.strip()

        if line.startswith("RESULT,"):
            fields = line.split(",")

            if len(fields) != 3:
                raise ValueError(
                    "Expected output format "
                    "'RESULT,n_aircraft,objective_per_passenger', "
                    f"but received: {line}"
                )

            reported_aircraft = int(fields[1])
            objective_per_passenger = float(fields[2])

            if reported_aircraft != number_of_aircraft:
                raise ValueError(
                    f"Requested {number_of_aircraft} aircraft, but "
                    f"main.py reported {reported_aircraft}."
                )

            return objective_per_passenger

        if line.startswith("NO_SOLUTION,"):
            print(f"No feasible solution for {number_of_aircraft} aircraft.")
            return None

    print(
        f"WARNING: No RESULT line found for {number_of_aircraft} aircraft. "
        "Check the required main.py output format."
    )
    print("main.py output:")
    print(completed.stdout)
    return None


# ---------------------------------------------------------------------
# MAIN SENSITIVITY ANALYSIS
# ---------------------------------------------------------------------

def main():
    if not MAIN_FILE.exists():
        raise FileNotFoundError(
            f"Could not find main.py in: {PROJECT_FOLDER}\n"
            "Place Sensitivity.py in the same folder as main.py."
        )

    aircraft_counts = range(
        FIRST_AIRCRAFT_COUNT,
        LAST_AIRCRAFT_COUNT + 1
    )

    results = []

    total_runs = LAST_AIRCRAFT_COUNT - FIRST_AIRCRAFT_COUNT + 1

    for run_number, number_of_aircraft in enumerate(aircraft_counts, start=1):
        print(
            f"Run {run_number}/{total_runs}: "
            f"{number_of_aircraft} aircraft"
        )

        value = run_scenario(number_of_aircraft)

        if value is not None:
            results.append({
                "Number of flights": number_of_aircraft,
                "Objective value per passenger": value
            })

    if not results:
        print(
            "\nNo results were collected. Check that main.py accepts the "
            "aircraft-count argument and prints the required RESULT line."
        )
        return

    data = pd.DataFrame(results)

    # Save the numerical results.
    data.to_csv(RESULTS_FILE, index=False)

    # Plot objective value per passenger against number of flights.
    plt.figure(figsize=(11, 6))
    plt.plot(
        data["Number of flights"],
        data["Objective value per passenger"],
        marker=".",
        markersize=4,
        linewidth=1.5
    )

    plt.xlabel("Number of flights")
    plt.ylabel("Objective function value per passenger")
    plt.title("Sensitivity Analysis: Objective Value per Passenger")
    plt.xlim(FIRST_AIRCRAFT_COUNT, LAST_AIRCRAFT_COUNT)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    plt.savefig(GRAPH_FILE, dpi=300)
    plt.show()

    print("\nSensitivity analysis completed.")
    print(f"Results saved to: {RESULTS_FILE}")
    print(f"Graph saved to:   {GRAPH_FILE}")


if __name__ == "__main__":
    main()
