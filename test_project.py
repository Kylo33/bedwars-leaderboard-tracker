import project
from data_for_tests import example_data
import unittest
from unittest import mock, TestCase
import datetime
import copy

# Here are my three root level functions

# 1

@mock.patch("project.datetime")
class TestDayList(TestCase):

    before_reset_days = ["2022-10-26", "2022-10-27", "2022-10-28", "2022-10-29", "2022-10-30", "2022-10-31", "2022-11-01"]
    after_reset_days = ["2022-10-27", "2022-10-28", "2022-10-29", "2022-10-30", "2022-10-31", "2022-11-01", "2022-11-02"]

    def test_before_7(self, datetime_mock):
        datetime_mock.datetime.now.return_value = datetime.datetime(2022, 11, 3, 0, 0, 0)
        datetime_mock.timedelta.side_effect = lambda *a, **kw: datetime.timedelta(*a, **kw)
        self.assertEqual(project.get_days(), self.before_reset_days)
    
    def test_before_730(self, datetime_mock):
        datetime_mock.datetime.now.return_value = datetime.datetime(2022, 11, 3, 7, 15, 0)
        datetime_mock.timedelta.side_effect = lambda *a, **kw: datetime.timedelta(*a, **kw)
        self.assertEqual(project.get_days(), self.before_reset_days)
        
    def test_after_8(self, datetime_mock):
        datetime_mock.datetime.now.return_value = datetime.datetime(2022, 11, 3, 10, 0, 0)
        datetime_mock.timedelta.side_effect = lambda *a, **kw: datetime.timedelta(*a, **kw)
        self.assertEqual(project.get_days(), self.after_reset_days)
    
    def test_after_730(self, datetime_mock):
        datetime_mock.datetime.now.return_value = datetime.datetime(2022, 11, 3, 7, 45, 0)
        datetime_mock.timedelta.side_effect = lambda *a, **kw: datetime.timedelta(*a, **kw)
        self.assertEqual(project.get_days(), self.after_reset_days)

# 2

class TestData(TestCase):

    @mock.patch("project.get_latest_date")
    @mock.patch("project.datetime")
    def setUp(self, mock_datetime, mock_latest_date):
        mock_datetime.datetime.now.return_value = datetime.datetime(2022, 11, 8, 0, 0, 0)
        mock_datetime.date.side_effect = lambda *a, **kw: datetime.date(*a, **kw)
        mock_datetime.timedelta.side_effect = lambda *a, **kw: datetime.timedelta(*a, **kw)
        mock_datetime.date.fromisoformat.side_effect = lambda a: datetime.date.fromisoformat(a)
        mock_latest_date.return_value = "2022-11-02"
        self.data = project.get_data("data_for_tests/example_database.db")

    def test_stuff(self):
        self.assertEqual(len(self.data), 100)
        for player in self.data:
            self.assertIsNotNone(player["position"])
            self.assertIsNotNone(player["uuid"])
            self.assertIsNotNone(player["username"])
            self.assertIsNotNone(player["total_by_date"])
            self.assertIsNotNone(player["total_wins"])
            assert "2022-10-30" not in player["total_by_date"]
            self.assertIsNotNone(player["daily_wins"])
            assert "2022-10-30" not in player["daily_wins"]
    
    def test_sorted(self):
        self.assertEqual(sorted(self.data, key=lambda s: s["total_by_date"]["2022-11-02"], reverse=True), self.data)

    def test_no_database(self):
        self.assertIsNotNone(self.data)
        self.data = project.get_data("this_database_doesnt_exist.db")
        self.assertIsNone(self.data)

# 3

class TestLatestDate(TestCase):
    def setUp(self):
        self.data = copy.deepcopy(example_data.example_data)
    
    def test_new_latest(self):
        self.assertEqual(project.get_latest_date(self.data), "2022-11-06")
        self.data[49]["total_by_date"]["2022-12-21"] = 10
        self.assertEqual(project.get_latest_date(self.data), "2022-12-21")
        self.data[49]["total_by_date"]["2025-01-01"] = 10
        self.assertEqual(project.get_latest_date(self.data), "2025-01-01")
        self.data[99]["total_by_date"]["2026-01-01"] = 10
        self.assertEqual(project.get_latest_date(self.data), "2026-01-01")
    
    def test_removed_latest(self):
        for item in self.data:
            item["total_by_date"].pop("2022-11-06")
        self.assertEqual(project.get_latest_date(self.data), "2022-11-05")
        for i in range(5):
            self.data[i]["total_by_date"].pop("2022-11-05")
        self.assertEqual(project.get_latest_date(self.data), "2022-11-05")


# not used to test functions on the same indentation level as main.
class TestLbTable(TestCase):
    
    @mock.patch("project.get_data")
    def setUp(self, data_mock):
        data_mock.return_value = example_data.example_data
        self.tbl = project.LbTable()

    def test_next_prev(self):
        tbl = project.LbTable()
        self.assertEqual(tbl.page, 0)
        tbl.next_page()
        self.assertEqual(tbl.page, 1)
        tbl.prev_page()
        self.assertEqual(tbl.page, 0)

    def test_find(self):
        self.assertEqual(self.tbl.find("PatExE").page, 1)
        self.assertEqual(self.tbl.find("KingDogo").page, 0)
        self.assertEqual(self.tbl.find("KyloFPS").page, 3)
        self.assertEqual(self.tbl.find("15y_").page, 9)
        self.assertEqual(self.tbl.find("OTDX").page, 9)

if __name__ == "__main__":
    unittest.main()