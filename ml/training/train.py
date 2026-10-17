"""Baseline training script.

    uv run python -m training.train                                  # demo on iris
    uv run python -m training.train --data ../data/train.csv --target label
    uv run python -m training.train --data ../data/train.csv --target price --task regression

Auto-detects numeric vs categorical columns, builds a sklearn Pipeline, reports a holdout
metric and saves the artifact the inference API loads.
"""

import argparse
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.datasets import load_iris
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, f1_score, mean_absolute_error, root_mean_squared_error
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from app.config import settings


def load_data(path: Path | None, target: str | None) -> tuple[pd.DataFrame, str]:
    if path is None:
        df = load_iris(as_frame=True).frame
        df["target"] = df["target"].map(dict(enumerate(load_iris().target_names)))
        return df, "target"
    if target is None:
        raise SystemExit("--target is required when --data is given")
    return (pd.read_parquet(path) if path.suffix == ".parquet" else pd.read_csv(path)), target


def infer_task(y: pd.Series) -> str:
    if y.dtype == object or y.dtype.name == "category" or y.nunique() <= 20:
        return "classification"
    return "regression"


def build_pipeline(X: pd.DataFrame, task: str) -> Pipeline:
    numeric = X.select_dtypes(include=np.number).columns.tolist()
    categorical = [c for c in X.columns if c not in numeric]
    pre = ColumnTransformer(
        [
            ("num", SimpleImputer(strategy="median"), numeric),
            (
                "cat",
                Pipeline(
                    [
                        ("impute", SimpleImputer(strategy="most_frequent")),
                        ("ohe", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
                    ]
                ),
                categorical,
            ),
        ]
    )
    est = (
        HistGradientBoostingClassifier()
        if task == "classification"
        else HistGradientBoostingRegressor()
    )
    return Pipeline([("pre", pre), ("model", est)])


def evaluate(task: str, y_true, y_pred) -> dict[str, float]:
    if task == "classification":
        return {
            "accuracy": float(accuracy_score(y_true, y_pred)),
            "f1_macro": float(f1_score(y_true, y_pred, average="macro")),
        }
    return {
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": float(root_mean_squared_error(y_true, y_pred)),
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--data", type=Path, help="CSV/Parquet with features + target (default: iris demo)"
    )
    p.add_argument("--target", help="Target column name")
    p.add_argument("--task", choices=["classification", "regression"], help="Default: inferred")
    p.add_argument("--out", type=Path, default=settings.model_path)
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()

    df, target = load_data(args.data, args.target)
    X, y = df.drop(columns=[target]), df[target]
    task = args.task or infer_task(y)

    stratify = y if task == "classification" else None
    X_tr, X_va, y_tr, y_va = train_test_split(
        X, y, test_size=0.2, random_state=args.seed, stratify=stratify
    )

    pipe = build_pipeline(X, task).fit(X_tr, y_tr)
    metrics = evaluate(task, y_va, pipe.predict(X_va))
    print(f"[{task}] validation:", metrics)

    # Refit on all data for the served model.
    pipe = build_pipeline(X, task).fit(X, y)

    example = {k: (v.item() if hasattr(v, "item") else v) for k, v in X.iloc[0].to_dict().items()}
    artifact = {
        "model": pipe,
        "version": datetime.now().strftime("%Y%m%d-%H%M%S"),
        "task": task,
        "target": target,
        "features": X.columns.tolist(),
        "metrics": metrics,
        "example": example,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, args.out)
    print(f"Saved {args.out} (version {artifact['version']})")


if __name__ == "__main__":
    main()
