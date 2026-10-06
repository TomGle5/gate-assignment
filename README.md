# Gate assignment experiments

This workspace contains small Python experiments for the airport gate assignment problem. The models assign aircraft to compatible gates while minimizing passenger walking distance, including arrival, departure, and transfer flows.

## Requirements

- Python 3
- Gurobi and a valid Gurobi license
- `matplotlib` for scripts that create Gantt charts
- `numpy` and `plotly` for `nonlinear.py`

The project virtual environment is `.venv`. Run scripts with its interpreter so the installed dependencies are available:

```bash
.venv/bin/python main.py
```

## Scripts

- `main.py`: primary stochastic model using the full airport distance matrix.
- `verification.py`: stochastic model with detailed passenger-flow and assignment checks.
- `validation.py`: earlier random-flow validation model.
- `validation2.py`: small deterministic two-aircraft transfer case.
- `nonlinear.py`: earlier nonlinear transfer-objective experiment.
- `claude-test.py`: compact basic GAP example based on the lecture formulation.
- `test.py`: generates and prints a small passenger-flow scenario.
- `DistanceMatrix.py`: distance data used by the primary model.
- `distancematrixvalidation.py`: reduced distance data for the validation case.

## Reproducibility

Most scripts use randomly generated schedules and passenger flows. Set the script's `random.seed(...)` call when a repeatable scenario is needed. The primary script leaves the seed commented out so each run can explore a new instance.

## Outputs

`main.py` prints schedules, gate assignments, and the optimized objective. `verification.py` also writes the passenger-flow matrix to `Pij.csv`. Plotting experiments may display a Gantt chart or create an image in the workspace.
