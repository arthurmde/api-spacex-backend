Blue Onion code challenge by Arthur de Moura Del Esposte
## Assumptions

* I created a CLI tool to perform the queries
* I did not remove entries with blank or incomplete values. Although they
  may be considered invalid, there is no specific requirement regarding invalid
  data in the challenge's description. Incomplete data may be useful in some contexts.
* The CLI app does not handle wrong inputs and other edge cases that
  are out of the scope of this challenge

## Setup

* Install python >= 3.10 on your machine to run the CLI application
* Install dependencies: `pip install -r requirements.txt`
* Install [Docker](https://docs.docker.com/engine/install/) and [Docker-Compose](https://docs.docker.com/compose/) to run TimescaleDB
* Run container services: `docker-compose up -d`. This command will run Timescaledb in a docker container sharing the port 5432 with your host.
  * If you want to access the database through the container, you can use the following
    authentication information:
      * user: postgres
      * password: pw4admin
* Run the tests: 
```bash
python3 -m unittest tests/test_base.py
```

## App Usage

The CLI application offers two possibilities:
#### last_position

You can query for the last position of a satellite at a given time. If no
time reference is provided, the system will consider the most recent data
available on the database. The following positional arguments must be provided:
* function_name
* satellite id
* time in ISO format (optional)

```bash
python3 api_spacex_backend last_position 5eed7715096e59000698572c 2021-01-26T02:30:00
#or
python3 api_spacex_backend last_position 5eed7715096e59000698572c
```

The satellite's position will be printed to the STDOUT

#### closest_satellite

You can query for the closest satellite of a given position on earth at a given time.
If no time reference is provided, the system will consider the most recent data
available on the database. The following positional arguments must be provided:
* function_name
* latitude
* longitude
* time in ISO format (optional)

```bash
python3 api_spacex_backend closest_satellite -40.4098530291677 108 2020-05-19T06:27:10
#or
python3 api_spacex_backend closest_satellite -40.4098530291677 108
```

The satellite's information will be printed to the STDOUT
## Solution formulation

This solution was created as a Python CLI tool based on the
[TimescaleDB](https://docs.timescale.com/) and [pyscopg3 lib](https://www.psycopg.org/psycopg3).

The details of each task are described below.
### Task 1
> Stand up your favorite kind of database (and ideally it would be in a form that would be runnable by us, via something like docker-compose).

This project uses [TimescaleDB](https://docs.timescale.com/),
a database that extends PostreSQL's capabilities to provide optimizations and
special features for time-series data.
It offers an abstraction layer called Hypertables to insert and query for
time-series data through SQL while hiding the underlying details on how data is
partitioned and stored.

One may run the TimescaleDB service through docker-compose available in this
repository.

### Task 2
>Write code (ideally in Python) to import the relevant fields in starlink_historical_data.json as a time series. The relevant fields are: - spaceTrack.creation_date (represents the time that the lat/lon records were recorded) - longitude - latitude - id (this is the starlink satellite id).

To import the relevant data to the database, the system relies on
[Postgres' Copy](https://www.postgresql.org/docs/current/sql-copy.html)
protocol which is one of the most efficient ways to load data
into the database. The script will
bulk insert the data extracted from the JSON file, organized as a list of tuples,
to the Hypertable in a single few operations.

### Task 3
> Write logic to fetch/query the last known position of a satellite (by id), given a time T. Include this query in your README or somewhere in the project submission

To allow users to query by the last known position of a satellite 
given a time T, the system will perform the following SQL query:
```sql
SELECT * FROM satellite_positions
WHERE satellite_id = '%s' AND time <= '%s'
ORDER BY time DESC
LIMIT 1;
```

The above query has two params, represented by `%s`, which will be replaced by
the informed satellite id and the given time in this order. For more details,
check the implementation of `SatellitePosition.last_position_for` static method
available in the [base module](api_spacex_backend/base.py).

### Task 4 (Bonus)
> Write some logic (via a combination of query + application logic, most likely) to fetch from the database the closest satellite at a given time T, and a given a position on a globe as a (latitude, longitude) coordinate.

To allow searching for the closest satellite at a given time T, and a given coordinate, I created a SQL query that uses aggregation functions such as
[Timescale's last function](https://docs.timescale.com/api/latest/hyperfunctions/last/#last) and MAX:
```sql
SELECT MAX(time) as max_time,
       satellite_id,
       last(latitude, time) as latitude,
       last(longitude, time) as longitude
FROM satellite_positions
WHERE time <= '%s' AND latitude IS NOT NULL AND longitude IS NOT NULL
GROUP BY satellite_id
ORDER BY max_time DESC;
```

Notice that this query removes entries with empty values for latitude or longitude.
This is important since we need a complete position to compare with the given location
in order to find the closest satellite. Therefore, this query considers the last
valid position for satellites at the given time.

With the query results, the system runs an algorithm to find the closest satellite to the
informed location based on [haversine function](https://github.com/mapado/haversine).
For more details, check the implementation of `SatellitePosition.closest_satellite` 
in the [base module](api_spacex_backend/base.py).