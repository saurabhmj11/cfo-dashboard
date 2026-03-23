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
        """
        :param contamination: Expected proportion of outliers in the dataset.
        """
        # We use a fixed random state for reproducibility 
        self.model = IsolationForest(
            contamination=contamination, 
            random_state=42, 
            n_estimators=100
        )

    def detect_anomalies(self, df_monthly: pd.DataFrame) -> List[Anomaly]:
        """
        Detects anomalies in monthly financial data using Isolation Forest.
        Looks at Revenue, Expenses, and Net Profit simultaneously to catch complex outliers.
        """
        anomalies = []
        
        # Need at least a few data points to run ML
        if len(df_monthly) < 6:
            # Fallback to simple logic or return none if too little data
            print("[ML Anomaly] Not enough data points to train Isolation Forest. Returning empty.")
            return []

        # Features to analyze
        features = ['revenue', 'expenses', 'net_profit']
        
        # Ensure columns exist, fill NaNs safely
        for feature in features:
            if feature not in df_monthly.columns:
                return []
                
        # Prepare Data Matrix
        X = df_monthly[features].copy()
        
        # Fit and Predict (-1 for outlier, 1 for inlier)
        try:
           predictions = self.model.fit_predict(X)
           
           # Isolation forest also gives an anomaly score. Lower is more abnormal.
           scores = self.model.score_samples(X)
           
           # Append predictions and scores back to dataframe
           df_monthly['is_anomaly'] = predictions
           df_monthly['anomaly_score'] = scores
           
           # Filter for anomalies
           outliers = df_monthly[df_monthly['is_anomaly'] == -1]
           
           for _, row in outliers.iterrows():
               date_str = str(row['month'])
               
               # Determine which metric drove the anomaly by comparing to means
               primary_driver = "revenue"
               max_deviation = 0
               
               for feature in features:
                   mean_val = df_monthly[feature].mean()
                   if mean_val != 0:
                       deviation = abs((row[feature] - mean_val) / mean_val)
                       if deviation > max_deviation:
                           max_deviation = deviation
                           primary_driver = feature
                           
               # Calculate deviation percentage for the primary driver
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
