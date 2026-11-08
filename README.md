# Smart Energy Meter: demand forecasting and conditional prepaid warnings

Soroti University, WSN2100. Deliverable 2, 6 November 2026.

Authors: Davis Twinomugisha, Sarah Asingwiire, Opuche Samson and Phillip Okwany.

This repository supplies the completed software part of Deliverable 2. It trains and evaluates electricity-demand forecasts, exports portable C models and runs a local HTTP demonstration. The selected model predicts the next full hour's consumption in kWh. Prepaid depletion estimates require an explicitly supplied starting balance in kWh and assume no top-up.

**Current boundary:** the electricity data are real public measurements from one French household. Assigned balances are constructed scenarios. Connected electricity sensing, ESP32 compilation/inference measurements, physical Wi-Fi tests, Ugandan household validation and utility balance integration remain pending. This is not evidence that the hardware functional-prototype gate has passed.

## Start here on Fedora or another Linux computer

1. Extract the project ZIP. Open a terminal inside the extracted `energy_d2` folder.
2. Create a Python 3.12 environment and install the pinned packages:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Python 3.12 was used for the supplied models. Install that Python version first if your terminal cannot find `python3.12`. Keep the pinned scikit-learn version when loading them. The dataset is already in the full ZIP. If you obtained only the Git repository, download it with `python scripts/download_data.py`.

3. Start the existing trained model. You do not need to retrain first:

```bash
python -m energy.server
```

4. Open **http://127.0.0.1:8765** in your browser. Select a recorded example and click **Calculate forecast**. Inspect the next-hour value, 24-hour recursive forecast, baseline comparisons and conditional depletion warning. Press Ctrl+C in the terminal to stop the server.

5. For an HTTP replay demonstration, leave the server running and open another terminal in the same folder:

```bash
source .venv/bin/activate
python scripts/replay_client.py
```

This sends recorded examples over local HTTP. It demonstrates the communication software, not a physical wireless link.

## Reproduce the experiment

```bash
python scripts/download_data.py
python -m energy.pipeline
python -m energy.export_c
python -m energy.plots
python -m unittest discover -s tests -v
python scripts/verify_integration.py
```

The C export check needs `g++`. On Fedora, install the C++ compiler if it is absent. Training uses CPU only and a fixed seed. The notebook `notebooks/Deliverable_2_Experiment.ipynb` contains the executed research workflow and can reproduce the same pipeline. Launch it from the project folder with a notebook environment if preferred. The browser dashboard needs no internet once packages are installed.

## Actual held-out results

| Method | Next-hour MAE, kWh | RMSE, kWh | R² |
|---|---:|---:|---:|
| 24-hour mean | 0.5344 | 0.6830 | 0.0837 |
| Persistence | 0.3887 | 0.5877 | 0.3216 |
| Same hour yesterday | 0.5078 | 0.7584 | -0.1298 |
| Decision tree | 0.3451 | 0.5004 | 0.5081 |
| Random forest, selected on validation | 0.3294 | 0.4758 | 0.5553 |

There are 4,805 test hours. Random-forest MAE is 38.36% lower than the 24-hour mean and 15.24% lower than persistence. A paired daily-block bootstrap gives a 36.17% to 40.59% interval for the improvement over the 24-hour mean. This assesses the same source household over time, not independent Ugandan homes.

For the constructed balance experiment, the 24-hour mean has slightly lower depletion-time MAE than the forest, 1.956 versus 2.010 hours on the common uncensored subset. Forest six-hour warning recall is higher, 92.68% versus 80.76%, with lower precision, 81.62% versus 91.69%. No claim of overall superior prepaid forecasting is supported yet.

## Files

| Path | Purpose |
|---|---|
| `reports/Deliverable_2_Report.pdf` | Eight-page D2 report |
| `reports/Deliverable_2_Report.md` | Editable report content |
| `notebooks/Deliverable_2_Experiment.ipynb` | Executed reproducible experiment |
| `energy/` | Cleaning, features, training, scenarios, C export and API |
| `models/` | Fitted Python models, feature schema and baseline definition |
| `data/raw/` | Unchanged UCI archive in the full ZIP, ignored by Git |
| `data/processed/` | Hourly energy and chronological feature tables |
| `results/` | Complete metrics, predictions, audit and software checks |
| `figures/` | Five figures derived from saved experimental results |
| `deployment/` | Portable C models and ESP32 public-data replay sketch |
| `web/` | Dashboard served by the local API |
| `docs/` | Dataset/model cards, demonstration, hardware handoff and submission checklist |

## GitHub submission

This capstone is separate from the earlier sensor laboratory submission. Use a capstone repository, not the unrelated lab repository. The package includes a Git bundle containing the project history. Follow `docs/GITHUB_SUBMISSION.md` to restore it or upload the extracted source files. A remote GitHub repository has not been created or published from this environment.

## Data attribution

Hebrail, G. and Berard, A. (2006). *Individual Household Electric Power Consumption*. UCI Machine Learning Repository. https://doi.org/10.24432/C58K54. Dataset licence: CC BY 4.0, https://creativecommons.org/licenses/by/4.0/.

The original ZIP is unchanged. Derived files aggregate minute power into complete-hour energy and construct causal features. These transformations are described in `docs/DATASET_CARD.md`; no author endorsement is implied.
