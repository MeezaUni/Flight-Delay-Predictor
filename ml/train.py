"""Train the Random Forest flight delay model.

Usage:
    python -m ml.train
    python -m ml.train --n-estimators 200 --min-samples-leaf 5
"""
import argparse
import json
import time
from datetime import datetime, timezone

import joblib
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OrdinalEncoder

from ml.config import (
    CATEGORICAL_FEATURES,
    FEATURES,
    METRICS_PATH,
    MODEL_PATH,
    MODELS_DIR,
    NUMERIC_FEATURES,
    RANDOM_STATE,
    TARGET,
    TEST_SIZE,
)
from ml.data import load_dataset, route_durations


def build_pipeline(n_estimators: int, max_depth: int | None, min_samples_leaf: int) -> Pipeline:
    preprocess = ColumnTransformer(
        [
            (
                "categorical",
                OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1),
                CATEGORICAL_FEATURES,
            ),
            ("numeric", "passthrough", NUMERIC_FEATURES),
        ],
        verbose_feature_names_out=False,
    )
    model = RandomForestClassifier(
        n_estimators=n_estimators,
        max_depth=max_depth,
        min_samples_leaf=min_samples_leaf,
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    return Pipeline([("preprocess", preprocess), ("model", model)])


def train(n_estimators: int, max_depth: int | None, min_samples_leaf: int) -> dict:
    print("Loading dataset...")
    df = load_dataset()
    X, y = df[FEATURES], df[TARGET]
    print(f"  {len(df):,} flights, {y.mean() * 100:.1f}% delayed")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y
    )
    print(f"  train: {len(X_train):,}  test: {len(X_test):,}")

    pipeline = build_pipeline(n_estimators, max_depth, min_samples_leaf)
    print("Training Random Forest...")
    started = time.perf_counter()
    pipeline.fit(X_train, y_train)
    train_seconds = time.perf_counter() - started
    print(f"  done in {train_seconds:.1f}s")

    y_pred = pipeline.predict(X_test)
    y_proba = pipeline.predict_proba(X_test)[:, 1]
    accuracy = accuracy_score(y_test, y_pred)
    report = classification_report(
        y_test, y_pred, target_names=["On time", "Delayed"], output_dict=True
    )
    cm = confusion_matrix(y_test, y_pred)

    feature_names = pipeline.named_steps["preprocess"].get_feature_names_out()
    importances = pipeline.named_steps["model"].feature_importances_
    feature_importance = sorted(
        ({"feature": name, "importance": float(value)} for name, value in zip(feature_names, importances)),
        key=lambda item: item["importance"],
        reverse=True,
    )

    metrics = {
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "model": "RandomForestClassifier",
        "params": {
            "n_estimators": n_estimators,
            "max_depth": max_depth,
            "min_samples_leaf": min_samples_leaf,
        },
        "train_seconds": round(train_seconds, 1),
        "dataset": {
            "rows": int(len(df)),
            "train_rows": int(len(X_train)),
            "test_rows": int(len(X_test)),
            "delay_rate": float(y.mean()),
        },
        "accuracy": float(accuracy),
        "roc_auc": float(roc_auc_score(y_test, y_proba)),
        "classification_report": report,
        "confusion_matrix": {
            "labels": ["On time", "Delayed"],
            "matrix": cm.tolist(),
        },
        "feature_importance": feature_importance,
    }

    print(f"Accuracy: {accuracy * 100:.2f}%   ROC AUC: {metrics['roc_auc']:.3f}")
    print(classification_report(y_test, y_pred, target_names=["On time", "Delayed"]))

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    bundle = {
        "pipeline": pipeline,
        "airlines": sorted(df["Airline"].unique().tolist()),
        "airports": sorted(set(df["AirportFrom"]) | set(df["AirportTo"])),
        "routes": route_durations(df),
        "metrics": metrics,
    }
    joblib.dump(bundle, MODEL_PATH, compress=3)
    METRICS_PATH.write_text(json.dumps(metrics, indent=2))
    size_mb = MODEL_PATH.stat().st_size / 1_000_000
    print(f"Saved model to {MODEL_PATH} ({size_mb:.1f} MB)")
    print(f"Saved metrics to {METRICS_PATH}")
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the flight delay model.")
    parser.add_argument("--n-estimators", type=int, default=100)
    parser.add_argument("--max-depth", type=int, default=None)
    parser.add_argument("--min-samples-leaf", type=int, default=10)
    args = parser.parse_args()
    train(args.n_estimators, args.max_depth, args.min_samples_leaf)


if __name__ == "__main__":
    main()
