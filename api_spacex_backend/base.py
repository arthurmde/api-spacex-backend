"""
api_spacex_backend base module.

This is the principal module of the api_spacex_backend project.
"""
import psycopg
import os
import json
from datetime import datetime

# example constant variable
NAME = "api_spacex_backend"
CONNECTION = "postgres://spacex:pw4admin@localhost:5432/spacex"

class DataImporter:
    """This class provides static methods to parse starlink_historical_data.json
    file and extract the relevant data for insertion into the database."""

    @staticmethod
    def build_relevant_data_as_array():
        """This method will build an array of tuples. Each tuple represents
        a Startlink's entry containing the relevant data for this project in
        as described below:
        [(time, id, latitude, longitude), ... ([time, id, latitude, longitude)]"""

        data = DataImporter.parse_json()
        result = []
        for entry in data:
            result.append((
                datetime.fromisoformat(entry['spaceTrack']['CREATION_DATE']),
                entry['id'],
                entry['latitude'],
                entry['longitude'],
            ))

        return result

    @staticmethod
    def parse_json():
        """This method parses the starlink_historical_data and returns a
        list of dictionaries with all the data from the file"""
        script_dir = os.path.dirname(__file__)
        FILE_PATH = os.path.join(script_dir, 'starlink_historical_data.json')

        with open(FILE_PATH, 'r') as json_file:
            data = json.load(json_file)
            return data


class DatabaseSetup:
    """This class provides static methods to handle the basic database setup,
    including schema definition and data inserting."""

    TABLE_NAME = 'satellite_positions'

    @staticmethod
    def setup_tables():
        """This method creates the table to store the positions of Starlink's
        satellites and turns it into a hypertable"""

        create_satellite_positions_table = """CREATE TABLE %s (
                                time  TIMESTAMP WITHOUT TIME ZONE NOT NULL,
                                satellite_id TEXT,
                                latitude DOUBLE PRECISION,
                                longitude DOUBLE PRECISION
                              );""" % (DatabaseSetup.TABLE_NAME)

        create_satellite_positions_hypertable = "SELECT create_hypertable('%s', 'time');" % (DatabaseSetup.TABLE_NAME)

        with psycopg.connect(CONNECTION) as conn:
            with conn.cursor() as curs:
                try:
                    curs.execute(create_satellite_positions_table)
                    curs.execute(create_satellite_positions_hypertable)
                    return True
                except psycopg.errors.DuplicateTable as error:
                    return False

    @staticmethod
    def drop_tables():
        """This method drops the existing tables and their data"""
        drop_table_query = "DROP TABLE %s;" % (DatabaseSetup.TABLE_NAME)
        with psycopg.connect(CONNECTION) as conn:
            with conn.cursor() as curs:
                try:
                    curs.execute(drop_table_query)
                    return True
                except psycopg.errors.UndefinedTable as error:
                    return False

    @staticmethod
    def populate():
        """This method inserts the relevant data of satellites positions inside the
        `satellite_positions` table by using Postgres' COPY protocol. It checks
        if the table already has data to avoid inserting the same data twice."""
        entries_count = DatabaseSetup.count_entries()

        data = DataImporter.build_relevant_data_as_array()
        copy_query = "COPY satellite_positions (time, satellite_id, latitude, longitude) FROM STDIN"

        with psycopg.connect(CONNECTION) as conn:
            with conn.cursor() as curs:
                if(entries_count == None or entries_count == 0):
                    with curs.copy(copy_query) as copy:
                        for entry in data:
                            copy.write_row(entry)
                    return True
                else:
                    return False

    @staticmethod
    def count_entries():
        """This utility methods returns the number of entries in satellite_positions
        table"""
        entries_count = 0
        db_entries_count_query = "SELECT COUNT(*) FROM %s;" % (DatabaseSetup.TABLE_NAME)
        with psycopg.connect(CONNECTION) as conn:
            with conn.cursor() as curs:
                entries_count = curs.execute(db_entries_count_query).fetchone()[0]

        return entries_count
