# Demonstration and likely panel questions

## Five-minute software demonstration

1. Open the eight-page report and show the revised consumption target and manual-balance condition.
2. Show `results/data_audit.json` and `data/processed/supervised_hourly.csv`: raw data, missing-hour policy, 15 features and chronological split.
3. Open the notebook and show the three baselines, two ML families, validation selection and frozen test metrics. Explain that lower MAE is better and R² is not percentage accuracy.
4. Start `python -m energy.server`, open http://127.0.0.1:8765 and calculate a recorded example. Change the assigned balance to show the conditional warning. Consumption forecasts do not change with balance because balance is not a model feature.
5. Run `python scripts/replay_client.py` in a second terminal. Show the HTTP response, payload size and host round-trip time. Label this host replay explicitly.
6. Show `results/deployment_checks.json`, the generated C header and the prepared ESP32 replay sketch. State that host C equivalence passes but target board and sensor evidence remain pending.

## Questions and answers

**What does the model learn?** Next full-hour electricity consumption from historical hourly energy and calendar features. It does not learn a real Yaka time-to-zero target.

**Why revise the proposal?** The supplied public dataset has consumption measurements but no prepaid credit or depletion events. Direct training on hours until Yaka depletion would require labels that do not exist here.

**Who is the first user?** A landlord or caretaker managing a shared prepaid connection. Tenants may benefit from an earlier advisory warning. Payment willingness and commercial viability are untested.

**Are the readings real or simulated?** Source consumption is recorded public data from France. Starting balances are assigned constructed scenarios. No Ugandan sensor readings or actual prepaid events have been collected for this implementation.

**Where does remaining balance come from?** The user enters a separately observed balance in kWh. The software has no utility account or balance integration. Meter account numbers and names do not reveal credit to this system.

**How did you prevent leakage?** All energy features precede the target hour; recursive forecasts use predicted future values. The split is chronological, the grid is fixed before fitting and model selection uses only validation MAE. Test labels never fit the models.

**Why no random train/test split?** Nearby hours are dependent and a random split would mix future observations into training. The intended task is forecasting later hours.

**Where is the moving average?** The 24-hour average is the main baseline and a model feature. Three- and six-hour means are additional features. All use completed earlier hours.

**Why not use an LSTM?** Two small tree families plus three simple baselines provide an implementable CPU comparison. Additional model complexity has not been shown necessary for this D2 scope.

**Is 38.36% the accuracy?** No. It is the relative reduction in next-hour MAE compared with the 24-hour mean. Forest MAE itself is 0.3294 kWh on the held-out period.

**Does the ML system beat the prepaid baseline?** It improves next-hour energy MAE. For constructed depletion time, the mean baseline is slightly better on common uncensored cases. Forest warnings capture more six-hour events but generate more false warnings. Overall prepaid superiority is not established.

**Why 24 hours of history?** It captures the most recent daily pattern while keeping the input buffer small. Other windows can be evaluated later using fresh validation data, not by repeatedly choosing on this test set.

**How does depletion calculation work?** Accumulate the 24 predicted hourly kWh values until they reach the supplied balance, then interpolate within the crossing hour under uniform hourly consumption. Report beyond 24 hours if no crossing is forecast.

**What if someone tops up?** The current scenario becomes invalid. A future integrated system must record the top-up and recompute from an updated verified balance.

**What does edge deployment mean at this stage?** The models are exported to portable C and checked against Python on a host compiler. A ready-to-adapt ESP32 replay sketch exists. Running it on the actual board and measuring its resources remains pending.

**Is the model below 100 KB?** The forest's constant arrays are 169,312 bytes, so it misses that aspirational target. The alternative tree needs 3,237 bytes of arrays. Compiled board flash and RAM still require measurement.

**Where can latency arise?** Sensor sampling, waiting for a complete hour, feature calculation, edge inference, Wi-Fi association, packet retries, transport and server processing. Host HTTP RTT is measured separately from board compute.

**Can this work offline?** C inference can run without a server once flashed and supplied with valid history. The prepared sketch still predicts during Wi-Fi disconnection, but live sensing storage, recovery and offline-alert behavior need hardware implementation and tests.

**Does this prove Ugandan applicability?** No. It provides a software benchmark and a testable local validation plan. Appliance patterns, climate and supply conditions may differ.

**What completes Deliverable 2?** A working connected sensing node, model running on the target board where feasible, physical communication evidence and an honest update to the report. The brief's functional-prototype gate remains open until that work is demonstrated.
