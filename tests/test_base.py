import api_spacex_backend.base
import math
import psycopg
import unittest

from datetime import datetime
from api_spacex_backend.base import DataImporter, DatabaseSetup, SatellitePosition

class TestDataImporter(unittest.TestCase):
    def test_parse_json(self):
        parsed_data = DataImporter.parse_json()
        self.assertEqual(len(parsed_data), 3141)
        self.assertTrue(type(parsed_data) is list)

    def test_build_relevant_data_as_array(self):
        data = DataImporter.build_relevant_data_as_array()
        self.assertEqual(len(data), 3141, "It has all entries")
        self.assertTrue(type(data) is list, "Extracted data to a python list")

        # Check data structure of internal tuples
        self.assertTrue(type(data[0]) is tuple, "Internal entry is a tuple")
        self.assertEqual(len(data[0]), 4, "Internal entry has 4 fields")

class TestDatabaseSetup(unittest.TestCase):
    def setUp(self):
        DatabaseSetup.drop_tables();

    def test_setup_and_drop_tables(self):
        query = "SELECT * FROM satellite_positions"

        self.assertTrue(DatabaseSetup.setup_tables(), "Creates the table")
        self.assertFalse(DatabaseSetup.setup_tables(), "It does not break when trying to create again")
        with psycopg.connect(api_spacex_backend.base.CONNECTION) as conn:
            with conn.cursor() as curs:
                self.assertTrue(curs.execute(query), "Query works")

        self.assertTrue(DatabaseSetup.drop_tables(), "Drops the table")
        self.assertFalse(DatabaseSetup.drop_tables(), "It does not break when trying to drop again")

        with psycopg.connect(api_spacex_backend.base.CONNECTION) as conn:
            with conn.cursor() as curs:
                with self.assertRaises(psycopg.errors.UndefinedTable) as context:
                    curs.execute(query)

                self.assertTrue('relation "satellite_positions" does not exist' in str(context.exception))

    def test_popuplate(self):
        DatabaseSetup.setup_tables()
        self.assertEqual(DatabaseSetup.count_entries(), 0, "Table is empty")

        self.assertTrue(DatabaseSetup.populate(), "Insert query works")
        self.assertEqual(DatabaseSetup.count_entries(), 3141, "Table is populated")

        self.assertFalse(DatabaseSetup.populate(), "It does not break when calling the method twice")

class TestSatellitePosition(unittest.TestCase):
    def setUp(self):
        DatabaseSetup.setup_tables()

    def test_last_position_for(self):
        DatabaseSetup.populate()

        satellite_id = '5f487be7d76203000692e59f'
        time_reference = '2021-01-26T05:00:00'

        # Query with a reference time
        result = SatellitePosition.last_position_for(satellite_id, time_reference)
        expected_result = (datetime.fromisoformat("2021-01-21T06:26:10"), '5f487be7d76203000692e59f', -40.4098530291677, 108)
        self.assertEqual(result, expected_result, "Query works with a specific time reference")

        # Query without a reference value
        result = SatellitePosition.last_position_for(satellite_id)
        expected_result = (datetime.fromisoformat("2021-01-26T14:16:09"), '5f487be7d76203000692e59f', -34.47530939181558, 161.0)
        self.assertEqual(result, expected_result, "Query works without a specific time reference")

    def test_closest_satellite(self):
        DatabaseSetup.populate()

        latitude = -40.4098530291677
        longitude = 108
        time_reference = '2020-05-19T06:27:10'

        # Query with a reference time
        satellite, distance = SatellitePosition.closest_satellite(latitude, longitude, time_reference)
        expected_satellite = (datetime.fromisoformat('2020-05-19T06:26:10'), '60106f20e900d60006e32cc3', 5.423581610589942, 2.0)
        self.assertEqual(satellite, expected_satellite, "Returned the expected satellite")
        self.assertEqual(math.trunc(distance), math.trunc(11750.732879114075), "Returned the expected distance")