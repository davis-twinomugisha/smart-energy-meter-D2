// Recorded public-data replay, NOT a connected electricity sensing prototype.
// Host C/C++ inference is verified. ESP32 compilation and radio operation are pending.
#include <WiFi.h>
#include <HTTPClient.h>
#include "energy_model.h"
#include "energy_features.h"
#include "replay_examples.h"
#if __has_include("wifi_config.h")
#include "wifi_config.h"
#else
const char* WIFI_SSID = "";
const char* WIFI_PASSWORD = "";
const char* SERVER_URL = "http://192.168.1.100:8765/api/telemetry";
#endif

size_t example_index=0;
unsigned long last_attempt=0;
void setup(){
  Serial.begin(115200);
  Serial.println("PUBLIC_DATA_REPLAY: UCI France. No sensor or utility balance.");
  if(strlen(WIFI_SSID)>0){WiFi.mode(WIFI_STA);WiFi.begin(WIFI_SSID,WIFI_PASSWORD);}
}
void loop(){
  if(millis()-last_attempt<5000)return;
  last_attempt=millis();
  const ReplayExample &e=REPLAY_EXAMPLES[example_index];
  float features[ENERGY_FEATURE_COUNT];
  energy_features(e.history,e.hour,e.weekday,features);
  unsigned long started=micros();
  float prediction=energy_model_predict(features);
  unsigned long compute_us=micros()-started;
  Serial.printf("replay=%u next_kwh=%.8f edge_inference_us=%lu\n",(unsigned)example_index,prediction,compute_us);
  if(WiFi.status()==WL_CONNECTED){
    String payload="{\"node_id\":\"ESP32_REPLAY_01\",\"data_mode\":\"public_data_replay\",\"forecast_start\":\"";
    payload+=e.timestamp;
    payload+="\",\"balance_kwh\":5,\"edge_prediction_kwh\":"+String(prediction,8)+",\"history_kwh\":[";
    for(int i=0;i<24;i++){if(i)payload+=",";payload+=String(e.history[i],8);}
    payload+="]}";
    HTTPClient http;http.setTimeout(5000);http.begin(SERVER_URL);
    http.addHeader("Content-Type","application/json");
    started=micros();int status=http.POST(payload);
    unsigned long roundtrip_us=micros()-started;
    Serial.printf("HTTP_status=%d payload_bytes=%u roundtrip_us=%lu\n",status,(unsigned)payload.length(),roundtrip_us);
    Serial.println(http.getString());http.end();
  }else Serial.println("Wi-Fi not connected. Local replay prediction still runs.");
  example_index=(example_index+1)%REPLAY_EXAMPLE_COUNT;
}
