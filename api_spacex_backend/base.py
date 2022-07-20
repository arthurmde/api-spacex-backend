"""
api_spacex_backend base module.

This is the principal module of the api_spacex_backend project.
"""
import psycopg
import os
import json
from datetime import datetime
from haversine import haversine

CONNECTION = "postgres://spacex:pw4admin@localhost:5432/spacex"
TABLE_NAME = 'satellite_positions'

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

    @staticmethod
    def setup_tables():
        """This method creates the table to store the positions of Starlink's
        satellites and turns it into a hypertable"""

        create_satellite_positions_table = """CREATE TABLE %s (
                                time  TIMESTAMP WITHOUT TIME ZONE NOT NULL,
                                satellite_id TEXT,
                                latitude DOUBLE PRECISION,
                                longitude DOUBLE PRECISION
                              );""" % (TABLE_NAME)

        create_satellite_positions_hypertable = "SELECT create_hypertable('%s', 'time');" % (TABLE_NAME)

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
        drop_table_query = "DROP TABLE %s;" % (TABLE_NAME)
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
        db_entries_count_query = "SELECT COUNT(*) FROM %s;" % (TABLE_NAME)
        with psycopg.connect(CONNECTION) as conn:
            with conn.cursor() as curs:
                entries_count = curs.execute(db_entries_count_query).fetchone()[0]

        return entries_count

class SatellitePosition:
    """This class provides an interface to query the satellite_positions table."""

    @staticmethod
    def print_time_data(time_data):
        """This method receives a tuple with positional data:
        * The time in which the position has been recorded
        * The satellite id
        * The latitude
        * The longitude
        """
        if(time_data == None):
            print("No results found")
            return

        time, satellite_id, latitude, longitude = time_data

        print(f'The position of the Satellite {satellite_id} at {time} is:')
        print(f'--> Latitude => {latitude}')
        print(f'--> Longitude => {longitude}')

    @staticmethod
    def last_position_for(satellite_id, time=None):
        """Query for the last position of the given satellite given a time reference.
        If no time reference is provided, the method will query for the
        most recent position of the satellite"""

        if time is None:
            time = datetime.now()

        query = """
                    SELECT * FROM satellite_positions
                    WHERE satellite_id = '%s' AND time <= '%s'
                    ORDER BY time DESC
                    LIMIT 1;
                """ % (satellite_id, time)

        result = None
        with psycopg.connect(CONNECTION) as conn:
            with conn.cursor() as curs:
                return curs.execute(query).fetchone()

    @staticmethod
    def closest_satellite(latitude, longitude, time=None):
        """This method returns the closest satellite of a given position on earth
        at an specific time.
        If no time reference is provided, the method will consider the most recent
        information."""

        if time is None:
            time = datetime.now()

        # Take advantage of Timescale's last funciton
        query = """
                    SELECT MAX(time) as max_time,
                            satellite_id,
                            last(latitude, time) as latitude,
                            last(longitude, time) as longitude
                    FROM satellite_positions
                    WHERE time <= '%s' AND latitude IS NOT NULL AND longitude IS NOT NULL
                    GROUP BY satellite_id
                    ORDER BY max_time DESC;
                """ % (time)

        result = None
        with psycopg.connect(CONNECTION) as conn:
            with conn.cursor() as curs:
                result = curs.execute(query).fetchall()

        # Find the closest satellite to the given place
        informed_place = (latitude, longitude)
        closest = None
        min_distance = None
        for satellite in result:
            satellite_position = (satellite[2], satellite[3])
            distance = haversine(informed_place, satellite_position)
            if min_distance == None or min_distance < distance:
                min_distance = distance
                closest = satellite

        return closest, min_distance