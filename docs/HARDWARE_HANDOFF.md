# Hardware and wireless handoff

Current evidence is host software only. No board has been compiled, flashed or connected. No energy sensor or physical Wi-Fi link has been tested.

## Prepared replay firmware

1. Open `deployment/esp32_replay/esp32_replay.ino` in the Arduino ESP32 toolchain for your exact board.
2. Copy `wifi_config.h.example` to `wifi_config.h` and set your Wi-Fi name/password and the computer's LAN URL. The actual file is ignored by Git.
3. Run `python -m energy.server --host 0.0.0.0` on the same trusted network. The default `127.0.0.1` binding works only for the computer itself. This local demonstration has no authentication or TLS.
4. Compile using a toolchain with C++17 hexadecimal-float literal support. Board compilation is pending. If your board/core rejects those literals, document the error before changing the export format.
5. Flash and open Serial Monitor at 115200. The sketch predicts one of three recorded public examples every five seconds, then posts JSON to `/api/telemetry` if Wi-Fi connects. Five seconds is the replay interval, not the training data's measurement interval.
6. Verify `data_mode=public_data_replay` and compare the returned edge/host prediction difference. Record actual latency, delivery status and payload size separately. Replay is still not connected electricity sensing.

To try the compact-tree alternative, include `compact_tree_model.h` and replace `energy_model_predict` with `compact_tree_model_predict`. Copy that header into the sketch folder first. Report which model you actually run. The forest is 169,312 bytes of constant arrays; the compact tree is 3,237 bytes. Board totals remain unknown.

## Complete the sensing node

- Confirm the selected ESP32 board and an approved isolated energy-measurement interface with the laboratory supervisor. Electrical installation must use the laboratory's approved method and supervision. This package does not prescribe mains wiring.
- Implement the selected meter/sensor driver. Humidity, light and motion readings from the earlier lab are not electricity-consumption training data.
- Integrate measured active power over time, or use differences in a verified cumulative kWh counter. Do not calculate real energy solely from voltage and current without valid power-factor information.
- Calibrate against a reference meter and log calibration error. Preserve the sampling interval, local clock and coverage. The current pipeline requires 60 valid minute averages per complete hour and 24 complete hourly histories.
- Add a timestamped hourly ring buffer, missing-data handling, restart recovery and clock synchronization. Until enough valid history exists, display insufficient history rather than an invented forecast.
- Supply balance manually in kWh only when independently observed. Reconcile every top-up and any balance correction in the local validation log. Current scenario code assumes no top-ups during its forecast horizon.

## Evidence to record after connection

| Measurement | Planned method | Status |
|---|---|---|
| Sensor accuracy | Matched reference-meter energy over known intervals | Pending |
| Board compile and flash | Board/core version, compiler log and firmware hash | Pending |
| Edge latency | Repeated `micros()` timings; median and p95, including warm-up policy | Pending |
| Flash/RAM | Compiled flash summary and runtime free/minimum heap | Pending |
| Wireless | At least 100 posts with sequence IDs, success/loss, RTT and payload bytes | Pending |
| Outage/recovery | Wi-Fi interruption, server restart, retained sensing history | Pending |
| Electrical cost | Independently measured idle and inference/communication energy | Pending |
| Local forecasting | Fixed later-period test with complete energy observations | Pending |
| Prepaid warnings | Independently observed balances, top-ups and event times | Pending |

HTTP response time includes parsing, host recursive forecasting, network transport and response handling. It is not edge inference latency. Hourly aggregation adds up to one sampling hour before a complete-hour update is available. The current five-second firmware loop is replay scheduling only. Do not replace these pending results with host timings.
