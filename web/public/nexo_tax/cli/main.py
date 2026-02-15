import argparse
import logging
from pathlib import Path

from nexo_tax.api import run as run_calculation

logger = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    parser = argparse.ArgumentParser(
        description="Finnish crypto tax calculator for Nexo cashback"
    )
    parser.add_argument(
        "csv_files", type=Path, nargs="+", help="Paths to Nexo CSV exports"
    )
    parser.add_argument(
        "--year",
        type=int,
        nargs="+",
        required=True,
        help="Tax year(s) to report (e.g. --year 2024 2025)",
    )
    parser.add_argument(
        "--audit-csv", action="store_true", help="Write detailed audit CSV files"
    )
    args = parser.parse_args()

    # Read CSV file contents
    csv_contents = []
    for csv_file in args.csv_files:
        with open(csv_file, encoding="utf-8") as f:
            csv_contents.append(f.read())

    # Run calculation via API
    result = run_calculation(csv_contents, args.year, args.audit_csv)

    # Print console output
    print(result["console"], end="")

    # Write audit files if requested
    if args.audit_csv:
        output_dir = Path("output")
        output_dir.mkdir(parents=True, exist_ok=True)
        for filename, content in result["audit_files"].items():
            filepath = output_dir / filename
            with open(filepath, "w", newline="") as f:
                f.write(content)
            logger.info("  Wrote %s", filepath)


if __name__ == "__main__":
    main()
