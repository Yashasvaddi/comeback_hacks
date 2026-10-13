
from __future__ import annotations

import csv
import logging
from collections import deque
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)

# Keep this order identical during training and inference.
SENSOR_COLUMNS = [
    "vib_de",
    "bearing_temp",
    "motor_current",
    "motor_winding_temp",
    "discharge_pressure",
    "flow",
    "suction_pressure",
    "vib_nde",
    "pump_speed",
    "seal_pot_level",
    "lube_oil_temp",
    "seal_pressure",
]

DEFAULT_WINDOW_SIZE = 10
DEFAULT_MODEL_PATH = (
    Path(__file__).resolve().parent.parent
    / "models"
    / "isolation_forest.joblib"
)


class AnomalyDetectionService:
    """
    Unsupervised sensor anomaly detector.

    Training:
        Fit an Isolation Forest using feature vectors generated from
        historical sensor records.

    Inference:
        Maintain recent sensor history and score each new record.

    The model detects unusual patterns; it does not independently
    diagnose equipment failures or authorize external notifications.
    """

    def __init__(
        self,
        model_path: Path | str = DEFAULT_MODEL_PATH,
        window_size: int = DEFAULT_WINDOW_SIZE,
        contamination: float = 0.05,
        random_state: int = 42,
    ) -> None:
        if window_size < 2:
            raise ValueError("window_size must be at least 2")

        self.model_path = Path(model_path)
        self.window_size = window_size
        self.contamination = contamination
        self.random_state = random_state

        self.model: Pipeline | None = None
        self.history: deque[dict[str, float]] = deque(
            maxlen=window_size
        )

        # Isolation Forest produces a decision score, not a calibrated
        # probability of equipment failure.
        self._feature_names: list[str] = []

    @staticmethod
    def _parse_record(
        record: dict[str, Any],
    ) -> dict[str, float]:
        """Validate and convert a CSV record into numeric sensor values."""
        parsed: dict[str, float] = {}

        missing = [
            name for name in SENSOR_COLUMNS
            if name not in record or record[name] in (None, "")
        ]
        if missing:
            raise ValueError(
                f"Missing sensor values: {', '.join(missing)}"
            )

        for name in SENSOR_COLUMNS:
            try:
                value = float(record[name])
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"Invalid numeric value for {name}: "
                    f"{record[name]!r}"
                ) from exc

            if not np.isfinite(value):
                raise ValueError(
                    f"Non-finite sensor value for {name}"
                )

            parsed[name] = value

        return parsed

    def _make_features(
        self,
        current: dict[str, float],
        previous_history: list[dict[str, float]],
    ) -> dict[str, float]:
        """
        Generate the same feature schema for training and inference.

        Features:
        - Current sensor readings
        - Difference from the previous reading
        - Rolling mean
        - Rolling standard deviation
        """
        features: dict[str, float] = {}

        history = previous_history + [current]
        recent = history[-self.window_size :]

        previous = (
            previous_history[-1]
            if previous_history
            else current
        )

        for name in SENSOR_COLUMNS:
            values = np.asarray(
                [row[name] for row in recent],
                dtype=np.float64,
            )

            features[f"{name}__current"] = current[name]
            features[f"{name}__delta"] = (
                current[name] - previous[name]
            )
            features[f"{name}__mean"] = float(np.mean(values))
            features[f"{name}__std"] = float(
                np.std(values, ddof=0)
            )

        return features

    def _features_for_training(
        self,
        records: list[dict[str, Any]],
    ) -> np.ndarray:
        """
        Build time-ordered feature vectors.

        Training uses only preceding rows and the current row, matching
        the feature generation used during streaming inference.
        """
        history: deque[dict[str, float]] = deque(
            maxlen=self.window_size
        )
        vectors: list[list[float]] = []

        for record in records:
            current = self._parse_record(record)
            features = self._make_features(
                current,
                list(history),
            )

            if not self._feature_names:
                self._feature_names = list(features.keys())

            vectors.append(
                [features[name] for name in self._feature_names]
            )
            history.append(current)

        return np.asarray(vectors, dtype=np.float64)

    def train_from_csv(
        self,
        csv_path: Path | str,
    ) -> dict[str, Any]:
        """
        Train on a CSV intended to represent normal operation.

        Important: the caller must verify that this dataset is a suitable
        normal baseline. Do not blindly train on a fault-containing file.
        """
        path = Path(csv_path)

        if not path.is_file():
            raise FileNotFoundError(
                f"Training CSV not found: {path}"
            )

        with path.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as file:
            reader = csv.DictReader(file)

            if not reader.fieldnames:
                raise ValueError(
                    f"CSV has no header: {path}"
                )

            missing = set(SENSOR_COLUMNS) - set(reader.fieldnames)
            if missing:
                raise ValueError(
                    "Training CSV is missing sensor columns: "
                    + ", ".join(sorted(missing))
                )

            records = list(reader)

        if len(records) < max(30, self.window_size * 3):
            raise ValueError(
                "Not enough training rows. Provide at least "
                f"{max(30, self.window_size * 3)} records; "
                f"received {len(records)}."
            )

        self._feature_names = []
        feature_matrix = self._features_for_training(records)

        self.model = Pipeline(
            steps=[
                ("scaler", StandardScaler()),
                (
                    "detector",
                    IsolationForest(
                        n_estimators=200,
                        contamination=self.contamination,
                        random_state=self.random_state,
                        n_jobs=-1,
                    ),
                ),
            ]
        )

        self.model.fit(feature_matrix)

        self.model_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        joblib.dump(
            {
                "model": self.model,
                "feature_names": self._feature_names,
                "sensor_columns": SENSOR_COLUMNS,
                "window_size": self.window_size,
                "contamination": self.contamination,
            },
            self.model_path,
        )

        logger.info(
            "Trained Isolation Forest on %d rows from %s",
            len(records),
            path,
        )

        return {
            "status": "trained",
            "training_rows": len(records),
            "feature_count": feature_matrix.shape[1],
            "window_size": self.window_size,
            "model_path": str(self.model_path),
        }

    def load_model(self) -> None:
        """Load a previously trained model from disk."""
        if not self.model_path.is_file():
            raise FileNotFoundError(
                f"Trained model not found: {self.model_path}. "
                "Train the model before starting inference."
            )

        saved = joblib.load(self.model_path)

        if saved.get("sensor_columns") != SENSOR_COLUMNS:
            raise ValueError(
                "The saved model uses a different sensor schema."
            )

        if saved.get("window_size") != self.window_size:
            raise ValueError(
                "The saved model's window size does not match "
                "the configured window size."
            )

        self.model = saved["model"]
        self._feature_names = saved["feature_names"]

        logger.info(
            "Loaded anomaly detector from %s",
            self.model_path,
        )

    def reset_history(self) -> None:
        """Reset rolling history after a dataset switch."""
        self.history.clear()

    def predict_record(
        self,
        record: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Score one incoming CSV row.

        The first rows may be scored using shorter history. The result
        includes history_size so the caller can apply a warm-up policy.
        """
        if self.model is None:
            raise RuntimeError(
                "Model is not loaded. Call load_model() first."
            )

        current = self._parse_record(record)
        previous_history = list(self.history)

        features = self._make_features(
            current,
            previous_history,
        )

        vector = np.asarray(
            [[features[name] for name in self._feature_names]],
            dtype=np.float64,
        )

        prediction = int(self.model.predict(vector)[0])
        decision_score = float(
            self.model.decision_function(vector)[0]
        )

        # Isolation Forest convention: -1 = anomaly, 1 = inlier.
        result = {
            "model": "isolation_forest",
            "prediction": (
                "anomaly" if prediction == -1 else "normal"
            ),
            "is_anomaly": prediction == -1,
            "decision_score": decision_score,
            "history_size": len(previous_history) + 1,
            "window_size": self.window_size,
            "sensor_values": current,
        }

        self.history.append(current)

        return result
