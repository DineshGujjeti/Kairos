import pandas as pd
from app.services.kpi.overview import overview
from app.services.kpi.calculator import compute_column_metrics
from app.services.kpi.alerts import generate_alerts


def dashboard(df: pd.DataFrame) -> dict:
    """
    Single endpoint returning everything needed for the dashboard frontend.
    Orchestrates overview, metrics, and alerts into one response.
    """
    return {
        "overview": overview(df),
        "metrics": compute_column_metrics(df),
        "alerts": generate_alerts(df),
        "timestamp": pd.Timestamp.now().isoformat(),
    }
