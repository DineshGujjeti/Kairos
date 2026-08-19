import pandas as pd


def generate_alerts(df: pd.DataFrame) -> dict:
    alerts = []
    
    numeric_df = df.select_dtypes(include="number")
    
    # High missing values
    for col in df.columns:
        missing_pct = (df[col].isna().sum() / len(df)) * 100
        if missing_pct > 50:
            alerts.append(f"Column '{col}' has {missing_pct:.1f}% missing values")
    
    # Duplicate rows
    duplicates = df.duplicated().sum()
    if duplicates > 0:
        alerts.append(f"Found {duplicates} duplicate rows ({(duplicates/len(df)*100):.1f}%)")
    
    # Negative values in non-ID columns
    for col in numeric_df.columns:
        if col not in ['id', 'ID', 'ID_', 'id_']:
            if (numeric_df[col] < 0).any():
                neg_count = (numeric_df[col] < 0).sum()
                alerts.append(f"Column '{col}' contains {neg_count} negative values")
    
    # High variance
    for col in numeric_df.columns:
        if len(numeric_df[col].dropna()) > 1:
            cv = numeric_df[col].std() / (numeric_df[col].mean() + 1e-10)
            if cv > 2:
                alerts.append(f"Column '{col}' has high variance (CV={cv:.2f})")
    
    # No numeric columns
    if numeric_df.empty:
        alerts.append("Dataset contains no numeric columns for analysis")
    
    return {
        "total_alerts": len(alerts),
        "alerts": alerts,
        "severity_high": len([a for a in alerts if "100%" in a or "missing" in a.lower()])
    }
