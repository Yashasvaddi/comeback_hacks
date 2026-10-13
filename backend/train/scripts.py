
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Resolve the backend directory so the script works when run directly.
BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.anamoly import (  # noqa: E402
    AnomalyDetectionService,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)

DEFAULT_DATASET = (
    BACKEND_DIR
    / "datasets"
    / "streaming"
    / "dataset_1.csv"
)

DEFAULT_MODEL_PATH = (
    BACKEND_DIR
    / "models"
    / "isolation_forest.joblib"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Train the CORTEX Isolation Forest anomaly detector "
            "using a baseline sensor CSV."
        )
    )

    parser.add_argument(
        "--data",
        type=Path,
        default=DEFAULT_DATASET,
        help="Path to the baseline CSV file.",
    )

    parser.add_argument(
        "--model",
        type=Path,
        default=DEFAULT_MODEL_PATH,
        help="Path where the trained model will be saved.",
    )

    parser.add_argument(
        "--window-size",
        type=int,
        default=10,
        help="Number of recent readings used for rolling features.",
    )

    parser.add_argument(
        "--contamination",
        type=float,
        default=0.05,
        help=(
            "Expected proportion of anomalies in the training data. "
            "This affects the model's default prediction threshold."
        ),
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not 0.0 < args.contamination <= 0.5:
        logger.error(
            "--contamination must be greater than 0 and at most 0.5"
        )
        return 2

    if args.window_size < 2:
        logger.error("--window-size must be at least 2")
        return 2

    if not args.data.is_file():
        logger.error("Dataset not found: %s", args.data)
        logger.error(
            "Check that the CSV exists under "
            "backend/datasets/streaming/."
        )
        return 1

    detector = AnomalyDetectionService(
        model_path=args.model,
        window_size=args.window_size,
        contamination=args.contamination,
    )

    try:
        result = detector.train_from_csv(args.data)
    except (ValueError, OSError) as exc:
        logger.exception("Model training failed: %s", exc)
        return 1

    # Reload the artifact to verify it can be loaded for inference.
    verification = AnomalyDetectionService(
        model_path=args.model,
        window_size=args.window_size,
        contamination=args.contamination,
    )

    try:
        verification.load_model()
    except (ValueError, OSError, KeyError) as exc:
        logger.exception("Saved model verification failed: %s", exc)
        return 1

    logger.info("Training completed successfully.")
    logger.info("Training rows: %s", result["training_rows"])
    logger.info("Feature count: %s", result["feature_count"])
    logger.info("Window size: %s", result["window_size"])
    logger.info("Saved model: %s", result["model_path"])
    logger.info("Model reload verification: passed")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
