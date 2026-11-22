"""Model comparison with expanding-window walk-forward validation."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.inspection import permutation_importance
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from transit.models.baseline import metrics, walk_forward

NUMERIC = ["lag_24", "lag_48", "lag_168", "roll_mean_24", "roll_mean_168", "temperature_2m", "precipitation",
           "wind_speed_10m", "is_holiday", "is_eve", "school_closed", "is_weekend", "hour_sin", "hour_cos"]
CATEGORICAL = ["hour", "dow", "month"]


def _models() -> dict:
    ridge = make_pipeline(
        ColumnTransformer([("num", StandardScaler(), NUMERIC),
                           ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL)]),
        Ridge(alpha=1.0))
    gbm = HistGradientBoostingRegressor(max_iter=400, learning_rate=0.05, max_leaf_nodes=31, random_state=0)
    models = {"Ridge": ridge, "Gradient boosting": gbm}
    try:
        from xgboost import XGBRegressor
        models["XGBoost"] = XGBRegressor(n_estimators=600, learning_rate=0.05, max_depth=6, subsample=0.8,
                                         colsample_bytree=0.8, random_state=0)
    except ImportError:
        pass
    return models


def compare(feats: pd.DataFrame, mode: str, n_folds: int = 4, test_days: int = 14):
    """Returns (per-fold metrics table, permutation importances of the best tree model on the last fold)."""
    df = feats[feats["transport_type"] == mode].dropna(subset=["lag_168", "roll_mean_168"]).reset_index(drop=True)
    X, y = df[NUMERIC + CATEGORICAL].fillna(0), df["passengers"].to_numpy(float)
    rows, last = [], None
    for k, (tr, te) in enumerate(walk_forward(df["timestamp"], n_folds=n_folds, test_days=test_days), 1):
        rows.append({"fold": k, "model": "Seasonal naive (last week)", **metrics(y[te], df["lag_168"].to_numpy()[te])})
        for name, model in _models().items():
            model.fit(X.iloc[tr], y[tr])
            pred = np.clip(model.predict(X.iloc[te]), 0, None)  # passenger counts cannot be negative
            rows.append({"fold": k, "model": name, **metrics(y[te], pred)})
            if name != "Ridge":
                last = (name, model, X.iloc[te], y[te])
    res = pd.DataFrame(rows)
    imp = None
    if last:
        name, model, Xte, yte = last
        pi = permutation_importance(model, Xte, yte, n_repeats=5, random_state=0, scoring="neg_mean_absolute_error")
        imp = (pd.DataFrame({"feature": Xte.columns, "importance": pi.importances_mean})
               .sort_values("importance", ascending=False).reset_index(drop=True))
        imp.attrs["model"] = name
    return res, imp


def summary(res: pd.DataFrame) -> pd.DataFrame:
    out = res.groupby("model")[["MAE", "sMAPE", "WAPE"]].mean().sort_values("WAPE")
    base = out.loc["Seasonal naive (last week)", "WAPE"]
    out["WAPE vs naive"] = (out["WAPE"] / base - 1) * 100
    return out.round(2)


def predictions_for_plot(feats: pd.DataFrame, mode: str, days: int = 14) -> pd.DataFrame:
    """Train the gradient-boosting model on everything except the last `days` and predict those days."""
    df = feats[feats["transport_type"] == mode].dropna(subset=["lag_168", "roll_mean_168"]).reset_index(drop=True)
    cut = df["timestamp"].max() - pd.Timedelta(days=days)
    tr, te = df[df["timestamp"] <= cut], df[df["timestamp"] > cut]
    m = HistGradientBoostingRegressor(max_iter=400, learning_rate=0.05, random_state=0)
    m.fit(tr[NUMERIC + CATEGORICAL].fillna(0), tr["passengers"])
    return pd.DataFrame({"timestamp": te["timestamp"], "actual": te["passengers"],
                         "predicted": np.clip(m.predict(te[NUMERIC + CATEGORICAL].fillna(0)), 0, None)})
