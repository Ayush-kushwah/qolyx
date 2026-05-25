import logging
import numpy as np
import shap
from typing import Any, Dict, List

logger = logging.getLogger("qolyx.anomaly")


class SHAPService:
    """Service to compute SHAP explainability for Isolation Forest anomalies."""

    @classmethod
    def explain_anomaly(
        cls, 
        model: Any, 
        feature_values: Dict[str, Any], 
        feature_names: List[str]
    ) -> Dict[str, float]:
        """Uses shap.TreeExplainer to get feature contributions for the given feature values."""
        # Prepare feature vector matching the model's feature names
        vector = []
        for feature in feature_names:
            val = None
            if feature == "row_count":
                val = feature_values.get("row_count")
            elif feature == "freshness_latency_seconds":
                val = feature_values.get("freshness_latency_seconds")
            elif feature.startswith("null_rate_"):
                col = feature[len("null_rate_"):]
                val = (feature_values.get("null_rates") or {}).get(col)
            elif feature == "mean_close_price":
                val = feature_values.get("mean_close_price")
            elif feature == "total_volume":
                val = feature_values.get("total_volume")
            elif feature == "unique_events_count":
                val = feature_values.get("unique_events_count")
                
            vector.append(float(val) if val is not None else 0.0)
            
        X = np.array([vector], dtype=float)
        
        try:
            # Isolation Forest is a tree-based ensemble, so we can use TreeExplainer
            explainer = shap.TreeExplainer(model)
            shap_values = explainer.shap_values(X)
            
            # Handle potential dimensions/formats of shap values
            if isinstance(shap_values, list):
                shap_vals = shap_values[0]
            else:
                shap_vals = shap_values
                
            if len(shap_vals.shape) > 1:
                shap_vals = shap_vals[0]
                
            importance = {}
            for name, val in zip(feature_names, shap_vals):
                importance[name] = float(val)
                
            return importance
        except Exception as exc:
            logger.error(f"Failed to generate SHAP values: {str(exc)}", exc_info=True)
            # Return fallback zero contribution for all features
            return {name: 0.0 for name in feature_names}

    @classmethod
    def generate_explanation(
        cls, 
        feature_importance: Dict[str, float], 
        anomaly_score: float, 
        anomaly_type: str
    ) -> str:
        """Generates a human-readable explanation of the anomaly based on SHAP feature importance."""
        # Sort features by their absolute SHAP values in descending order to find the largest drivers
        sorted_features = sorted(
            feature_importance.items(),
            key=lambda x: abs(x[1]),
            reverse=True
        )
        
        # Get top 3 contributors with absolute SHAP value > 1e-4
        top_contributors = [
            (name, val) 
            for name, val in sorted_features 
            if abs(val) > 1e-4
        ]
        
        if not top_contributors:
            return (
                f"Anomaly of type '{anomaly_type}' detected with score {anomaly_score:.2f}. "
                f"No individual feature contributed significantly to the detection."
            )
            
        reasons = []
        for name, val in top_contributors[:3]:
            # A negative SHAP value in Isolation Forest pushes the decision function lower (more anomalous)
            role = "anomalous deviation" if val < 0 else "variance contribution"
            reasons.append(f"'{name}' ({role}, SHAP: {val:.4f})")
            
        reasons_str = ", ".join(reasons)
        return (
            f"Anomaly of type '{anomaly_type}' detected with score {anomaly_score:.2f}. "
            f"The primary driver(s) are: {reasons_str}."
        )
