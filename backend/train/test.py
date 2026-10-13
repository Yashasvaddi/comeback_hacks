
import csv
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.anamoly import AnomalyDetectionService

MODEL_PATH = BACKEND_DIR / "models" / "isolation_forest.joblib"
DATASET_PATH = (
    BACKEND_DIR / "datasets" / "streaming" / "cortex_synthetic_pump_telemetry_1000.csv"
)


def main():
    detector = AnomalyDetectionService(
        model_path=MODEL_PATH,
        window_size=10,
    )
    detector.load_model()

    normal = 0
    anomalous = 0

    with DATASET_PATH.open(
        "r", encoding="utf-8-sig", newline=""
    ) as file:
        reader = csv.DictReader(file)

        for row in reader:
            result = detector.predict_record(row)

            if result["is_anomaly"]:
                anomalous += 1
                label = "ANOMALY"
            else:
                normal += 1
                label = "NORMAL"

            print(
                f'{row.get("timestamp", "unknown")} | '
                f'{label} | '
                f'score={result["decision_score"]:.4f}'
            )

    print("\n=== Evaluation Summary ===")
    print(f"Normal predictions: {normal}")
    print(f"Anomalous predictions: {anomalous}")
    print(f"Total predictions: {normal + anomalous}")


if __name__ == "__main__":
    main()
