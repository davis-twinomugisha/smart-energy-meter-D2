# Model card

Task: next full-hour electricity consumption regression, kWh. Intended use is a research demonstration for an eventual landlord/caretaker monitoring node. It does not authenticate to a utility, read a meter balance, disconnect supply, bill tenants or establish commercial readiness.

Training: one French household, chronological train/validation/test split and fixed seed 20261106. Baselines: 24-hour mean, last-hour persistence and same hour yesterday. Search: 8 decision-tree and 4 random-forest configurations, all specified before fitting in `experiment_protocol.json`. Selection: validation MAE only. Selected forest: 32 trees, depth at most 8, minimum leaf size 12. Final fit uses train plus validation. Selected compact tree: see `results/model_selection.json` for its validation-selected configuration.

Inputs: exactly 24 consecutive complete hourly energy totals, oldest first, plus the next-hour timestamp in a consistent local clock. Missing or invalid histories are rejected. Scaling: none. Output is nonnegative energy. A 24-hour trajectory recursively feeds each prediction back into the history; forecast errors can therefore accumulate. The next-hour test metrics are not 24-hour trajectory metrics.

Primary test MAE: 0.3294 kWh; RMSE 0.4758 kWh; R² 0.5553; WAPE 34.51%. WAPE is absolute error divided by total observed energy, not classification accuracy. The daily-block bootstrap reflects variation within the same historical household and does not establish cross-household generalization or correct for all long-term dependence.

Conditional warning comparison does not establish dominance: the 24-hour mean slightly wins depletion-time MAE; the forest increases six-hour warning recall with more false warnings. No probability calibration or prediction intervals have been established. The chosen six-hour threshold is a fixed experimental setting, not a demonstrated optimal service threshold.

C export uses float32 constants and features, with double accumulation, not integer quantization. Both exports are checked on all 32,449 eligible rows. Forest constant arrays total 169,312 bytes, exceeding the aspirational 100 KB budget even before board linking. Compact-tree arrays total 3,237 bytes and offer a lower-storage alternative. These are array payloads, not board flash or RAM readings. The forest remains the validation-selected predictive model; deployment choice must be finalized after actual board resource tests.

Risks: changing household routines, appliance mix, climate, time conventions, missing data and old single-site training data can affect forecasts. A current meter balance must be supplied separately and verified; tariffs, account numbers and names cannot be used to infer remaining kWh. Utility balances and real depletion events require a verified lawful acquisition method. Keep predictions advisory until local validation is complete.
