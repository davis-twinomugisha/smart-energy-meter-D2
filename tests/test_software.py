import unittest
from datetime import datetime
from pathlib import Path
import json
import numpy as np
import pandas as pd
import joblib
from energy.features import make_features,validate_history,parse_time,FEATURE_NAMES
from energy.depletion import exhaustion_time,forecast_path,baseline_paths
from energy.server import Predictor

ROOT=Path(__file__).resolve().parents[1]

class FeaturesAndBalance(unittest.TestCase):
    def test_feature_order_and_units(self):
        h=np.arange(1,25,dtype=float)
        f=make_features(h,datetime(2026,11,6,12))
        np.testing.assert_array_equal(f[:6],[24,23,22,19,13,1])
        np.testing.assert_allclose(f[6:10],[23,21.5,12.5,np.std(h)],rtol=1e-6)
        self.assertEqual(len(f),len(FEATURE_NAMES))
    def test_insufficient_or_invalid_history(self):
        for values in [[],[1]*23,[1]*25,[float('nan')]*24,[-1]*24,[float('inf')]*24]:
            with self.assertRaises(ValueError):validate_history(values)
    def test_hour_alignment(self):
        with self.assertRaises(ValueError):parse_time('2026-11-06T12:01:00')
        with self.assertRaises(ValueError):parse_time('not-a-date')
    def test_exhaustion_interpolation(self):
        self.assertEqual(exhaustion_time([1,2,1],2),1.5)
        self.assertEqual(exhaustion_time([1,2],0),0)
        self.assertIsNone(exhaustion_time([0,0,0],1))
        self.assertIsNone(exhaustion_time([1,2],4))
        self.assertEqual(exhaustion_time([1,2],3),2)
    def test_invalid_balances(self):
        for b in [-1,float('nan'),float('inf'),True]:
            with self.assertRaises(ValueError):exhaustion_time([1,2],b)
    def test_recursive_forecast_has_no_future_readings(self):
        class Dummy:
            def predict(self,x):return np.array([x[0,0]+1])
        p=forecast_path(Dummy(),[1]*24,datetime(2026,11,6,0),3)
        self.assertEqual(p,[2,3,4])
    def test_baselines(self):
        b=baseline_paths(list(range(24)))
        self.assertEqual(b['mean_24h'],[11.5]*24)
        self.assertEqual(b['persistence'],[23]*24)
        self.assertEqual(b['same_hour_yesterday'],list(range(24)))

class DatasetAndModels(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.table=pd.read_csv(ROOT/'data/processed/supervised_hourly.csv',parse_dates=['hour_start']).set_index('hour_start')
        cls.hourly=pd.read_csv(ROOT/'data/processed/hourly_energy.csv',parse_dates=['hour_start']).set_index('hour_start')
    def test_time_splits_are_ordered(self):
        d=self.table
        self.assertLess(d[d.split=='train'].index.max(),d[d.split=='validation'].index.min())
        self.assertLess(d[d.split=='validation'].index.max(),d[d.split=='test'].index.min())
    def test_features_use_only_previous_hours(self):
        # Independently reconstruct at timestamps across the full experiment.
        for t,row in self.table.iloc[::250].iterrows():
            h=self.hourly.energy_kwh.reindex(pd.date_range(t-pd.Timedelta(hours=24),periods=24,freq='h'))
            self.assertTrue(h.notna().all())
            f=make_features(h.to_numpy(),t.to_pydatetime())
            np.testing.assert_allclose(f,row[FEATURE_NAMES].to_numpy(dtype=float),rtol=2e-6,atol=1e-7)
            self.assertAlmostEqual(row.target_kwh,self.hourly.loc[t,'energy_kwh'],places=8)
    def test_incomplete_hour_is_never_imputed(self):
        d=self.hourly
        self.assertTrue(d.loc[d.valid_minutes.ne(60),'energy_kwh'].isna().all())
    def test_stored_test_predictions_match_frozen_model(self):
        model=joblib.load(ROOT/'models/selected_model.joblib')
        if hasattr(model,'n_jobs'):model.n_jobs=1
        test=self.table[self.table.split=='test']
        result=pd.read_csv(ROOT/'results/test_predictions.csv')
        name=json.loads((ROOT/'results/evaluation.json').read_text())['selected_family']
        actual=model.predict(test[FEATURE_NAMES].to_numpy(dtype=np.float32))
        np.testing.assert_allclose(actual,result[name],rtol=2e-6,atol=1e-7)
    def test_source_country_is_explicit(self):
        audit=json.loads((ROOT/'results/data_audit.json').read_text())
        self.assertEqual(audit['source_country'],'France')
        self.assertEqual(audit['source_households'],1)

class PredictionAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.predictor=Predictor()
    def test_example_forecast_and_conditional_balance(self):
        example=self.predictor.examples()[0]
        result=self.predictor.predict(example)
        self.assertEqual(len(result['forecast_24h_kwh']),24)
        self.assertGreaterEqual(result['next_hour_kwh'],0)
        self.assertTrue(result['balance_scenario']['assumes_no_topups'])
        self.assertEqual(result['data_mode'],'public_data_replay')
    def test_invalid_payloads(self):
        for p in [None,[],{}, {'history_kwh':[0]*24,'forecast_start':'bad'}]:
            with self.assertRaises((ValueError,TypeError)):self.predictor.predict(p)
    def test_missing_balance_is_unavailable_not_zero(self):
        result=self.predictor.predict({'history_kwh':[.5]*24,'forecast_start':'2026-11-06T12:00:00'})
        self.assertIsNone(result['balance_scenario'])

if __name__=='__main__':unittest.main()
