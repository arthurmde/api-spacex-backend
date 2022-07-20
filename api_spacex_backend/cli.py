"""CLI interface for api_spacex_backend project.
"""

from base import DatabaseSetup, SatellitePosition
from datetime import datetime
import sys

def handle_last_position():
    satellite_id = sys.argv[2]
    time = None
    if(len(sys.argv) == 4):
        time = sys.argv[3]

    result = SatellitePosition.last_position_for(satellite_id, time)
    SatellitePosition.print_time_data(result)

def handle_closest_satellite():
    latitude = float(sys.argv[2])
    longitude = float(sys.argv[3])
    time = None
    if(len(sys.argv) == 5):
        time = sys.argv[4]

    satellite, min_distance = SatellitePosition.closest_satellite(latitude, longitude, time)
    print("This is the record of the closest satellite found:")
    SatellitePosition.print_time_data(satellite)
    print(f'--> Distance from the given location => {min_distance} KMs')

def main(*arguments):  # pragma: no cover
    """
    The main function executes on commands:
    `python -m api_spacex_backend` and `$ api_spacex_backend `.

    This is your program's entry point.
    """
    print('\nLoading database and data...\n')
    DatabaseSetup.setup_tables()
    DatabaseSetup.populate()

    selected_function = sys.argv[1]

    match selected_function:
        case "last_position":
            handle_last_position()
        case "closest_satellite":
            handle_closest_satellite()
        case _:
            print("The available functions are: 'last_position' and 'closest_satellite'. Check the README for more details.");

    print('\nFinished.')