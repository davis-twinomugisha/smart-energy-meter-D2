#pragma once
#include <math.h>

// h[0] is the oldest and h[23] the latest completed hourly kWh measurement.
// hour=forecast hour (0..23), weekday=Monday 0 through Sunday 6.
static inline void energy_features(const float h[24],int hour,int weekday,float x[15]) {
  const int lags[6]={1,2,3,6,12,24};
  for(int i=0;i<6;i++)x[i]=h[24-lags[i]];
  double s3=0,s6=0,s24=0;
  for(int i=0;i<24;i++){
    s24+=h[i];if(i>=21)s3+=h[i];if(i>=18)s6+=h[i];
  }
  double mean=s24/24.0,ss=0;
  for(int i=0;i<24;i++){double d=h[i]-mean;ss+=d*d;}
  x[6]=(float)(s3/3.0);x[7]=(float)(s6/6.0);x[8]=(float)mean;x[9]=(float)sqrt(ss/24.0);
  const double pi=3.14159265358979323846;
  x[10]=(float)sin(2*pi*hour/24.0);x[11]=(float)cos(2*pi*hour/24.0);
  x[12]=(float)sin(2*pi*weekday/7.0);x[13]=(float)cos(2*pi*weekday/7.0);
  x[14]=(weekday>=5)?1.0f:0.0f;
}
