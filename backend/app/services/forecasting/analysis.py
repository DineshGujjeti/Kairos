"""
Trend and seasonality analysis for time series data with robust error handling.
"""
import numpy as np
import pandas as pd


def detect_trend(values: list[float] | np.ndarray) -> dict:
    """
    Detect trend: increasing, decreasing, or stable.
    Handles edge cases: empty data, single value, constant values.
    """
    values = np.array(values)
    
    if len(values) < 2:
        return {"direction": "stable", "slope": 0.0, "strength": 0.0}
    
    # Handle constant values
    if np.std(values) == 0:
        return {"direction": "stable", "slope": 0.0, "strength": 0.0}
    
    # Simple slope: (last - first) / len
    slope = float((values[-1] - values[0]) / len(values))
    
    # Strength: relative to mean (avoid division by zero)
    non_zero_mask = values != 0
    if np.any(non_zero_mask):
        mean_val = np.mean(np.abs(values[non_zero_mask]))
    else:
        mean_val = 1.0
    
    strength = abs(slope) / abs(mean_val) if mean_val != 0 else 0.0
    
    if abs(slope) < 1e-6:
        direction = "stable"
    elif slope > 0:
        direction = "increasing"
    else:
        direction = "decreasing"
    
    return {
        "direction": direction,
        "slope": round(float(slope), 4),
        "strength": round(float(min(strength, 1.0)), 4),  # Cap strength at 1.0
    }


def detect_seasonality(values: list[float] | np.ndarray, min_period: int = 7) -> dict:
    """
    Detect seasonality with improved heuristics and edge case handling.
    """
    values = np.array(values)
    
    if len(values) < min_period * 2:
        return {
            "is_seasonal": False,
            "detected_period": None,
            "strength": 0.0,
            "message": "Insufficient data to detect seasonality",
        }
    
    # Handle constant values
    if np.std(values) == 0:
        return {
            "is_seasonal": False,
            "detected_period": None,
            "strength": 0.0,
            "message": "Target values are constant (no seasonality)",
        }
    
    best_period = None
    best_score = 0.0
    
    for period in range(min_period, len(values) // 2 + 1):
        n_chunks = len(values) // period
        if n_chunks < 2:
            continue
        
        chunks = [values[i * period:(i + 1) * period] for i in range(n_chunks)]
        chunk_means = [np.mean(chunk) for chunk in chunks]
        
        if len(chunk_means) > 1:
            variance = np.var(chunk_means)
            overall_variance = np.var(values)
            
            if overall_variance > 0:
                score = 1.0 - (variance / overall_variance)
            else:
                score = 0.0
            
            if score > best_score:
                best_score = score
                best_period = period
    
    if best_period and best_score > 0.3:
        return {
            "is_seasonal": True,
            "detected_period": best_period,
            "strength": round(float(best_score), 4),
            "message": f"Detected {best_period}-step seasonal pattern",
        }
    else:
        return {
            "is_seasonal": False,
            "detected_period": None,
            "strength": 0.0,
            "message": "No clear seasonal pattern detected",
        }


def compute_confidence_interval(
    forecast_values: list[float],
    historical_values: list[float],
    confidence: float = 0.95,
) -> dict:
    """
    Compute prediction intervals based on residual standard error.
    Handles edge cases: empty data, single value, constant values.
    """
    forecast_values = np.array(forecast_values)
    historical_values = np.array(historical_values)
    
    # Use recent values for std estimation
    if len(historical_values) >= 10:
        recent = historical_values[-10:]
    else:
        recent = historical_values
    
    # Handle constant values
    if len(recent) > 0:
        residual_std = float(np.std(recent))
    else:
        residual_std = 0.0
    
    # Z-score for confidence level
    z_scores = {0.68: 1.0, 0.95: 1.96, 0.99: 2.576}
    z = z_scores.get(confidence, 1.96)
    
    margin = z * residual_std
    
    return {
        "confidence_level": int(confidence * 100),
        "lower_bounds": [round(float(v - margin), 4) for v in forecast_values],
        "upper_bounds": [round(float(v + margin), 4) for v in forecast_values],
    }
