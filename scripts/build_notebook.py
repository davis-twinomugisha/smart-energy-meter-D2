"""Construct and execute a portable notebook using the actual shared pipeline."""
from pathlib import Path
import base64,contextlib,io,json,os,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));os.chdir(ROOT)

def main():
    cells=[];namespace={};count=0
    def md(s):cells.append({'cell_type':'markdown','metadata':{},'source':s.splitlines(keepends=True)})
    def code(s,images=()):
        nonlocal count
        count+=1;stdout=io.StringIO()
        with contextlib.redirect_stdout(stdout):exec(compile(s,f'notebook-cell-{count}','exec'),namespace)
        outputs=[]
        if stdout.getvalue():outputs.append({'output_type':'stream','name':'stdout','text':stdout.getvalue().splitlines(keepends=True)})
        for name in images:
            outputs.append({'output_type':'display_data','metadata':{},'data':{'image/png':base64.b64encode((ROOT/name).read_bytes()).decode(),'text/plain':[name]}})
        cells.append({'cell_type':'code','execution_count':count,'metadata':{},'source':s.splitlines(keepends=True),'outputs':outputs})
        print('Executed notebook cell',count,flush=True)
    md('# Deliverable 2: Electricity-demand forecasting\nSoroti University, WSN2100. 6 November 2026.\n\nDavis Twinomugisha, Sarah Asingwiire, Opuche Samson and Phillip Okwany.\n\nThis notebook was executed on the full recorded UCI dataset. It predicts next-hour consumption, not observed prepaid depletion. Assigned balances below are constructed scenarios. Hardware, physical wireless and Ugandan validation remain pending.\n\nRun from the extracted project folder or its notebooks directory after installing requirements.txt. CPU only. All model selection uses validation data; the test period remains held out from fitting.')
    code('from pathlib import Path\nimport os, sys, json\nimport numpy as np\nimport pandas as pd\nROOT = Path.cwd()\nif ROOT.name == "notebooks": ROOT = ROOT.parent\nos.chdir(ROOT)\nsys.path.insert(0, str(ROOT))\nfrom energy.pipeline import prepare, train, scenarios\nfrom energy.features import FEATURE_NAMES\nprotocol = json.loads(Path("experiment_protocol.json").read_text())\nprint(protocol["primary_research_question"])\nprint(protocol["hypothesis"])\nprint("Model selection:", protocol["selection"])')
    md('## 1. Verify, clean and aggregate actual source measurements\nMinute-averaged active power is in kW. Sum 60 valid minute values and divide by 60 to obtain complete-hour kWh. Reject incomplete hours and histories with gaps. No missing values are imputed. Calendar timestamps remain on the original source clock.\n\nSource: Hebrail and Berard (2006), UCI, https://doi.org/10.24432/C58K54. CC BY 4.0. One household in Sceaux, France.')
    code('hourly, table, audit = prepare()\nprint("Split summary:")\nprint(table.groupby("split", sort=False).size().to_string())\nprint("Features:", FEATURE_NAMES)')
    md('## 2. Fit baselines and two small model families\nThe predeclared grid has eight decision-tree and four random-forest configurations. Validation MAE chooses configuration and family. Refit the family winners on train plus validation, then evaluate the frozen models. Baselines use only prior observed hours. No test-driven hyperparameter changes are made.')
    code('model, evaluation = train(hourly, table)\nprint("95% paired daily-block interval for MAE improvement (%):", evaluation["daily_block_bootstrap_95pct_interval_percent"])\nprint(evaluation["generalization_scope"])')
    md('## 3. Conditional balance experiment\nAssign balances of 2, 5, 10 and 20 kWh to complete daily test origins. Compare depletion from observed future energy with depletion from 24-hour forecast trajectories. These are assigned scenarios, not actual prepaid events. The forest rolls forward recursively with predictions only, so multi-hour error can accumulate. Depletion outside 24 hours is censored.')
    code('if hasattr(model, "n_jobs"): model.n_jobs = 1\nscenarios(hourly, table, model)\nscenario = json.loads(Path("results/constructed_scenario_metrics.json").read_text())\nprint(pd.DataFrame(scenario["methods"])[["method", "scenarios", "common_uncensored_scenarios", "MAE_hours_common_subset", "warning_precision", "warning_recall"]].to_string(index=False))\nprint(scenario["limitations"])')
    md('## 4. Figures from frozen results\nThe forecast figure uses the first seven chronological test days, not a hand-picked high-performing interval. The 24-hour mean slightly outperforms the forest on constructed depletion-time MAE, while the forest has higher six-hour warning recall and more false warnings. A gain in next-hour MAE does not establish superior real prepaid warnings.')
    code('from energy.plots import main as make_plots\nmake_plots()\n# Jupyter displays these saved figures; the standalone executor embeds them too.\ntry:\n    from IPython.display import display, Image\nexcept ImportError:\n    print("Figures are saved in figures/ and embedded in this notebook.")\nelse:\n    for filename in ["01_test_mae.png", "02_test_forecast.png", "04_error_diagnostics.png", "05_constructed_scenarios.png"]:\n        display(Image(filename=str(Path("figures") / filename)))',images=['figures/01_test_mae.png','figures/02_test_forecast.png','figures/04_error_diagnostics.png','figures/05_constructed_scenarios.png'])
    md('## 5. Deployment evidence and limits\nGenerated C models were compiled on the host and compared with Python for all eligible feature rows. Board compilation, flash/RAM, latency and radio tests are pending. The forest exceeds the aspirational 100 KB array budget; a smaller validation-selected tree is also supplied. Run `python -m energy.export_c` to regenerate these checks with g++.')
    code('deployment = json.loads(Path("results/deployment_checks.json").read_text())\nprint(json.dumps(deployment, indent=2))')
    md('## 6. Software API example\nThis executes the same predictor used by the local HTTP dashboard. The public recorded history is real; the entered 5 kWh balance is assigned. The optional remaining time is conditional on forecasts and no top-ups.')
    code('from energy.server import Predictor\npredictor = Predictor()\nexample = predictor.examples()[0]\nresponse = predictor.predict(example)\nprint(json.dumps({k: response[k] for k in ["forecast_start", "next_hour_kwh", "balance_scenario", "data_mode", "scope"]}, indent=2))')
    md('## 7. Conclusions and next experiments\nThe selected forest reduces held-out next-hour MAE by 38.36% relative to the 24-hour mean for this source household. This meets the predeclared 10% consumption-error target. The constructed depletion findings are mixed. They do not validate real prepaid warnings or Ugandan applicability.\n\nNext: connect an approved energy sensor and ESP32, measure actual model resources and Wi-Fi behavior, collect consented local energy plus verified balances/top-ups, and evaluate a later untouched local period. Keep the same baseline and report false warnings, missed events, lead time, censoring and sample dependence. See the hardware handoff and full report.')
    out=ROOT/'notebooks';out.mkdir(exist_ok=True)
    book={'nbformat':4,'nbformat_minor':5,'metadata':{'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},'language_info':{'name':'python','version':'3.12.3'}},'cells':cells}
    for i,c in enumerate(book['cells']):c['id']=f'd2-cell-{i+1:02d}'
    (out/'Deliverable_2_Experiment.ipynb').write_text(json.dumps(book,indent=1))
    print('Saved executed notebook with',count,'code cells.')

if __name__=='__main__':main()
