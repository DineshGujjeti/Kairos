"""
Module 5: Enterprise Forecasting Engine.

Provides time-series forecasting capabilities with automatic model selection,
seasonal decomposition, confidence intervals, and comprehensive evaluation metrics.

Service modules:
- loader: Load and prepare data for forecasting
- detector: Auto-detect datetime and target columns
- overview: Time-series shape and characteristics
- train: Train forecasting models (Prophet fallback to Linear Regression/MA)
- predict: Generate predictions and confidence intervals
- evaluate: Model evaluation metrics and diagnostics
- seasonality: Seasonal decomposition and detection
- trend: Trend analysis and extraction
- confidence: Confidence interval calculation
- dashboard: Unified forecasting dashboard
- report: Comprehensive forecasting report
"""
