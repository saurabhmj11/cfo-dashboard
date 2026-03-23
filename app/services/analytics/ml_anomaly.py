import pandas as pd
from typing import List
from sklearn.ensemble import IsolationForest
import numpy as np

from app.models.schemas import Anomaly

class MLAnomalyDetector:
    """
    Service responsible for fast, deterministic anomaly detection using pre-trained ML models.
    Replaces basic Z-Score math with robust multivariate outlier detection.
    """
    
    def __init__(self, contamination: float = 0.1):
        self.model = IsolationForest(
            contamination=contamination, 
            random_state=42, 
            n_estimators=100
        )

    def detect_anomalies(self, df_monthly: pd.DataFrame) -> List[Anomaly]:
        anomalies = []
        
        if len(df_monthly) < 6:
            return []

        features = ['revenue', 'expenses', 'net_profit']
        for feature in features:
            if feature not in df_monthly.columns:
                return []
                
        X = df_monthly[features].copy()
        
        try:
           predictions = self.model.fit_predict(X)
           scores = self.model.score_samples(X)
           
           df_monthly['is_anomaly'] = predictions
           df_monthly['anomaly_score'] = scores
           
           outliers = df_monthly[df_monthly['is_anomaly'] == -1]
           
           for _, row in outliers.iterrows():
               date_str = str(row['month'])
               primary_driver = "revenue"
               max_deviation = 0
               
               for feature in features:
                   mean_val = df_monthly[feature].mean()
                   if mean_val != 0:
                       deviation = abs((row[feature] - mean_val) / mean_val)
                       if deviation > max_deviation:
                           max_deviation = deviation
                           primary_driver = feature
                           
               mean_driver = df_monthly[primary_driver].mean()
               dev_pct = ((row[primary_driver] - mean_driver) / mean_driver) * 100 if mean_driver != 0 else 0
               
               anomalies.append(Anomaly(
                   date=date_str,
                   metric=primary_driver,
                   value=float(row[primary_driver]),
                   deviation_percent=float(dev_pct),
                   severity="High" if row['anomaly_score'] < -0.7 else "Medium",
                   description=f"ML detected systemic anomaly driven by {primary_driver} deviation."
               ))
               
        except Exception as e:
            print(f"[ML Anomaly Engine] Error during Isolation Forest detection: {e}")
            
        return anomalies

ml_anomaly_detector = MLAnomalyDetector()
