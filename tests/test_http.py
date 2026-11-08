import json,threading,unittest,urllib.request,urllib.error
from http.server import ThreadingHTTPServer
from energy.server import Predictor,make_handler

class HTTPIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.predictor=Predictor()
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),make_handler(cls.predictor))
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.url='http://127.0.0.1:'+str(cls.server.server_port)
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join()
    def request(self,path,body=None,kind='application/json'):
        data=None if body is None else (body if isinstance(body,bytes) else json.dumps(body).encode())
        req=urllib.request.Request(self.url+path,data=data,headers={'Content-Type':kind})
        try:
            with urllib.request.urlopen(req,timeout=10) as response:return response.status,response.read()
        except urllib.error.HTTPError as e:return e.code,e.read()
    def test_dashboard_and_status(self):
        status,body=self.request('/');self.assertEqual(status,200);self.assertIn(b'Energy',body)
        status,body=self.request('/api/status');self.assertFalse(json.loads(body)['hardware_connected'])
    def test_real_request_predicts(self):
        example=self.predictor.examples()[0]
        status,body=self.request('/api/predict',example)
        self.assertEqual(status,200);self.assertEqual(len(json.loads(body)['forecast_24h_kwh']),24)
    def test_bad_json_and_content_type(self):
        self.assertEqual(self.request('/api/predict',b'{oops')[0],400)
        self.assertEqual(self.request('/api/predict',{},'text/plain')[0],400)
        self.assertEqual(self.request('/api/predict',b'')[0],400)
    def test_body_limit_and_unknown_routes(self):
        self.assertEqual(self.request('/api/predict',b'x'*32769)[0],400)
        self.assertEqual(self.request('/missing')[0],404)
        self.assertEqual(self.request('/missing',{})[0],404)
    def test_nonfinite_values_are_rejected(self):
        p=self.predictor.examples()[0];p['history_kwh'][0]=float('nan')
        self.assertEqual(self.request('/api/predict',p)[0],400)
    def test_telemetry_requires_provenance(self):
        p=self.predictor.examples()[0];p.pop('data_mode')
        self.assertEqual(self.request('/api/telemetry',p)[0],400)
        p['data_mode']='public_data_replay';p['edge_prediction_kwh']=.5
        status,body=self.request('/api/telemetry',p)
        self.assertEqual(status,200);self.assertIn('edge_host_absolute_difference_kwh',json.loads(body))

if __name__=='__main__':unittest.main()
