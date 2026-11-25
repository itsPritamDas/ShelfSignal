import unittest
import pandas as pd

from app.services.forecasting import engineer_features, FEATURES


class FeatureEngineeringTests(unittest.TestCase):
    def test_lag_features_start_after_28_observations(self):
        dates = pd.date_range("2024-01-01", periods=40, freq="D")
        frame = pd.DataFrame({
            "date": dates,
            "store_id": "STORE_01",
            "product_id": "P001",
            "unit_price": 50.0,
            "promotion": 0,
            "holiday": 0,
            "sales_units": list(range(10, 50)),
        })
        result = engineer_features(frame)
        self.assertEqual(len(result), 12)
        self.assertEqual(result.iloc[0]["lag_1"], 37)
        self.assertTrue(all(column in result.columns for column in FEATURES))

    def test_series_are_grouped_independently(self):
        dates = pd.date_range("2024-01-01", periods=40, freq="D")
        first = pd.DataFrame({"date": dates, "store_id": "STORE_01", "product_id": "P001",
                              "unit_price": 10, "promotion": 0, "holiday": 0, "sales_units": 5})
        second = first.copy()
        second["product_id"] = "P002"
        second["sales_units"] = 50
        result = engineer_features(pd.concat([first, second], ignore_index=True))
        first_row = result[result["product_id"] == "P001"].iloc[0]
        second_row = result[result["product_id"] == "P002"].iloc[0]
        self.assertEqual(first_row["lag_1"], 5)
        self.assertEqual(second_row["lag_1"], 50)


if __name__ == "__main__":
    unittest.main()
