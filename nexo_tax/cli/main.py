import argparse
import logging
from pathlib import Path

from nexo_tax.calculator import (
    build_lot_queue,
    compute_annual_summary,
    compute_card_analysis,
)
from nexo_tax.fx import FxRateTable
from nexo_tax.parser import parse_csvs
from nexo_tax.report import (
    print_card_analysis,
    print_summary,
    write_audit_csv,
    write_card_analysis_csv,
)

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

    # 1. Parse all CSVs into a merged, date-sorted result
    result = parse_csvs(args.csv_files)
    logger.info("Parsed %d cashback events", len(result.cashback_events))
    logger.info(
        "Parsed %d cashback reversal events", len(result.cashback_reversal_events)
    )
    logger.info("Parsed %d interest events", len(result.interest_events))
    logger.info("Parsed %d exchange buy events", len(result.exchange_buy_events))
    logger.info(
        "Parsed %d FX observations (card purchases)",
        len(result.fx_observations),
    )
    logger.info("Parsed %d disposal events", len(result.disposal_events))
    logger.info("Parsed %d card purchase events", len(result.card_purchase_events))
    logger.info("Parsed %d repayment events", len(result.repayment_events))

    # 2. Build FX rate table from all observations
    fx = FxRateTable(result.fx_observations)

    # 3. Apply EUR values to all events
    for ev in result.cashback_events:
        ev.value_eur = fx.convert_usd_to_eur(ev.value_usd, ev.date)

    for ev in result.cashback_reversal_events:
        ev.value_eur = fx.convert_usd_to_eur(ev.value_usd, ev.date)

    for ev in result.interest_events:
        ev.value_eur = fx.convert_usd_to_eur(ev.value_usd, ev.date)

    for ev in result.exchange_buy_events:
        ev.value_eur = fx.convert_usd_to_eur(ev.value_usd, ev.date)

    for ev in result.disposal_events:
        ev.proceeds_eur = fx.convert_usd_to_eur(ev.proceeds_usd, ev.date)

    # 4. Build per-asset FIFO lot queues from ALL acquisition sources (across years)
    lots_by_asset = build_lot_queue(
        result.cashback_events, result.interest_events, result.exchange_buy_events
    )

    # 5. Process each year sequentially (lots carry forward via FIFO)
    for year in sorted(args.year):
        summary = compute_annual_summary(
            year,
            result.cashback_events,
            result.cashback_reversal_events,
            result.interest_events,
            result.exchange_buy_events,
            result.disposal_events,
            lots_by_asset,
        )
        print_summary(summary)

        # Card cashback profitability analysis
        net_cashback_eur = (
            summary.total_cashback_eur - summary.total_cashback_reversal_eur
        )
        card_analysis = compute_card_analysis(
            year,
            result.card_purchase_events,
            result.repayment_events,
            net_cashback_eur,
        )
        print_card_analysis(card_analysis)

        if args.audit_csv:
            output_dir = Path("output")
            write_audit_csv(
                output_dir,
                year,
                result.cashback_events,
                result.interest_events,
                lots_by_asset,
                summary,
            )
            write_card_analysis_csv(
                output_dir,
                card_analysis,
                result.card_purchase_events,
                result.repayment_events,
            )


if __name__ == "__main__":
    main()
