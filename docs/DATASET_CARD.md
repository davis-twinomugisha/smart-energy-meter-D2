# Dataset and target

Source: Hebrail, G. and Berard, A. (2006), Individual Household Electric Power Consumption, UCI, DOI https://doi.org/10.24432/C58K54. Source page: https://archive.ics.uci.edu/dataset/235/individual+household+electric+power+consumption. Retrieved 6 November 2026. CC BY 4.0: https://creativecommons.org/licenses/by/4.0/.

Coverage is one household in Sceaux, France, December 2006 to November 2010. The 2,075,259 minute records are observed public measurements. They are not our Arduino readings and are not Ugandan rental data. Original date/time and `Global_active_power` are used. Other channels are unnecessary for this causal consumption-only model. Source active power is minute-averaged kW.

## Processing decisions

- Verify the unchanged archive against the SHA-256 recorded in `results/data_audit.json`.
- Parse date/time strictly; order timestamps and reject duplicates.
- Treat missing, nonnumeric, nonfinite and negative active power as invalid.
- Convert each full hour into kWh using sum of its 60 minute-averaged kW values divided by 60.
- Require all 60 valid minutes. Mark incomplete hours missing, including partial first and final hours. Do not impute or replace missing readings with zero.
- Require 24 consecutive complete hours before every forecast and a complete target hour.
- Preserve the original source clock. No conversion to Uganda time or claim of DST resolution is made.

There are 25,979 invalid/missing power entries, 34,589 hourly bins, 34,085 complete hours and 32,449 eligible labelled feature rows. Excluding 504 incomplete hours also removes subsequent examples whose histories overlap the gaps. No outliers were removed solely because the load was large. No scaling or oversampling is used for tree regression.

## Features and split

Forecast timestamp t means predict energy over [t, t+1 hour) using observations ending before t. Features are lags 1, 2, 3, 6, 12 and 24 hours; preceding 3-, 6- and 24-hour means; population standard deviation of the preceding 24 hours; sine/cosine of target hour and weekday; and weekend flag. There are 15 features in the exact order specified in `models/feature_schema.json`.

Split the hourly timeline before dropping invalid examples: first 70% train, next 15% validation, final 15% test. Eligible rows: train 22,818; validation 4,826; test 4,805. Counts need not equal exactly 70/15/15 after gap exclusion. Label hours are disjoint. Validation/test histories may include earlier observations, as in online forecasting. No future target enters a feature. Hyperparameters are selected using validation MAE only, then models are refitted on train plus validation before frozen testing.

## Prepaid scenarios

There are no observed prepaid balances, utility account data, top-ups or depletion-event labels. The secondary experiment assigns 2, 5, 10 and 20 kWh to 193 eligible daily origins in the test period, producing 772 constructed scenarios. Measured future consumption determines the constructed crossing; recursive forecast consumption gives the predicted crossing. Uniform consumption is assumed within a crossing hour, with no top-ups. Beyond 24 hours is censored, not assigned an invented precise depletion time. Cases sharing an origin are dependent. These scenarios cannot establish real-world prepaid performance.

## Local data collection template

`data/templates/local_hourly_template.csv` is a header-only schema, not collected data. Append verified complete hourly energy and coverage from the selected sensor. Record the site, timestamp convention, calibration, outages, top-ups and any independently observed balance in separate consented logs. The local hourly schema is an ingestion contract; an adapter for a specific sensor remains to be implemented after the hardware is chosen.
