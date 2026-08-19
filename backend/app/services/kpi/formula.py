import re
import pandas as pd
from app.core.exceptions import FormulaError, ColumnNotFoundError


def safe_evaluate_formula(df: pd.DataFrame, formula: str) -> dict:
    """
    Safely evaluate a formula like "revenue - cost" or "price * quantity".
    Blocks dangerous operations, validates column references.
    """
    formula = formula.strip()
    
    # Check for dangerous patterns first
    dangerous = ['import', '__', 'lambda', 'exec', 'eval', 'open', 'system', 'globals', 'locals']
    for word in dangerous:
        if word in formula.lower():
            raise FormulaError(f"Formula contains disallowed operation: {word}")
    
    # Extract potential column names (word characters, spaces)
    potential_cols = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b', formula)
    
    # Filter to actual columns
    columns_used = set(col for col in potential_cols if col in df.columns)
    
    # Check all columns exist
    for col in potential_cols:
        if col not in df.columns and col not in ['and', 'or', 'not', 'True', 'False']:
            if col not in ['e']:  # Allow scientific notation like 1e-5
                raise ColumnNotFoundError(col)
    
    # Safe evaluation: only allow operations
    safe_dict = {col: df[col] for col in columns_used}
    safe_dict['pd'] = pd
    
    try:
        result = eval(formula, {"__builtins__": {}}, safe_dict)
        
        if isinstance(result, pd.Series):
            # Convert to dict with string keys for JSON serialization
            values_dict = {str(k): float(v) if pd.notna(v) else None for k, v in result.to_dict().items()}
            return {
                "formula": formula,
                "result_type": "series",
                "values": values_dict,
                "stats": {
                    "mean": float(result.mean()),
                    "sum": float(result.sum()),
                    "min": float(result.min()),
                    "max": float(result.max()),
                }
            }
        elif isinstance(result, (int, float)):
            return {
                "formula": formula,
                "result_type": "scalar",
                "value": float(result),
            }
        else:
            return {
                "formula": formula,
                "result_type": "other",
                "value": str(result),
            }
    except Exception as e:
        raise FormulaError(f"Formula evaluation failed: {str(e)}")
