import unittest
import pandas as pd
from ramsc.panel import month_key, load_raw_datasets, build_public_panel


class PanelDateTests(unittest.TestCase):
    def test_missing_month_stays_missing(self):
        result = month_key(pd.Series([pd.Timestamp('2024-01-13'), pd.NaT]))
        self.assertEqual(result.iloc[0], '2024-01')
        self.assertTrue(pd.isna(result.iloc[1]))

    def test_source_task_dates_match_explicit_us_format(self):
        _, _, tasks = load_raw_datasets()
        expected = pd.to_datetime(tasks['Tech Sign Off Date'], format='%m/%d/%Y', errors='raise')
        pd.testing.assert_series_equal(tasks['Tech Sign Off Date_dt'], expected, check_names=False)
        self.assertEqual(expected.isna().sum(), tasks['Tech Sign Off Date'].isna().sum())

    def test_panel_window_and_conservation(self):
        panel, summary = build_public_panel()
        self.assertTrue(panel.month.between('2024-01', '2026-03').all())
        self.assertFalse(panel.duplicated(['pt_id', 'month', 'ata2']).any())
        self.assertEqual(summary.months, 27)
        self.assertEqual(summary.total_removals, 1668)
        self.assertAlmostEqual(summary.total_flight_hours, 33486.6)
        self.assertEqual(set(panel.loc[panel.low_exposure, 'pt_id']), {'AC-01', 'AC-18', 'AC-23'})



if __name__ == '__main__':
    unittest.main()
