"""Export Table M-1 (Maintainability burden by ATA system)."""

from pathlib import Path

from ramsc.maintainability import export_maintainability

if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent
    table, meta = export_maintainability(root)
    print("Table M-1 exported.")
    print(f"  Total man-hours : {meta['total_manhours']:,.2f} h")
    print(f"  Linked WOs      : {meta['total_linked_work_orders']}")
    print(f"  ALHWO excluded  : {meta['alhwo_total_docs']} docs / {meta['alhwo_total_removals']} removals")
    print(f"  Multi-ATA docs  : {meta['multi_ata_docs']} ({meta['multi_ata_pct']}%)")
    print(f"  Top ATA         : {meta['top_ata']:02d} ({meta['top_ata_label']}) — "
          f"{meta['top_ata_manhours']:,.1f} h ({meta['top_ata_share_pct']}% of fleet total)")
    print("  LaTeX  -> latex/manuscript/tables/table_m1_maintainability.tex")
    print("  CSV    -> analysis_outputs/public/table_m1_maintainability.csv")
