import pandas as pd

from app.services.eda.preview import preview
from app.services.eda.summary import summary
from app.services.eda.statistics import statistics
from app.services.eda.missing_values import missing_values
from app.services.eda.correlation import correlation
from app.services.eda.outliers import outliers
from app.services.eda.distribution import distribution
from app.services.eda.quality import quality
from app.services.eda.insights import insights


def report(df: pd.DataFrame) -> dict:
    """
    Generate a complete Exploratory Data Analysis (EDA) report.

    This function orchestrates all EDA modules and returns a
    single consolidated response.

    The report is intentionally modular so that each analysis
    component can evolve independently while maintaining a
    stable API for clients.
    """

    return {
        "preview": preview(df),
        "summary": summary(df),
        "statistics": statistics(df),
        "missing_values": missing_values(df),
        "correlation": correlation(df),
        "outliers": outliers(df),
        "distribution": distribution(df),
        "quality": quality(df),
        "insights": insights(df),
    }