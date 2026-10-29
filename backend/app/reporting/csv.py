import csv
from pathlib import Path
from typing import Sequence, Union


def write_csv_rows(filepath: Union[str, Path], fieldnames: Sequence[str], rows: Sequence[dict]) -> Path:
    out_path = Path(filepath)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(fieldnames))
        writer.writeheader()
        writer.writerows(rows)
    return out_path
