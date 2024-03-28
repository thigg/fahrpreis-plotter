import argparse
import logging
import sqlite3
from collections import defaultdict
from datetime import datetime, timedelta
from enum import Enum
from sqlite3 import Cursor
from typing import Dict, List, Tuple, Generator, Any

import plotly.express as px
from plotly.graph_objs import Figure


class Query_Datatype(Enum):
    travel_duration = {'column': 'travel_duration', 'column_idx': 2, 'z_divisor': 1000 * 60 * 60,
                       'z_axis_name': "Dauer (Stunden)"}
    price_cents = {'column': 'price_cents', 'column_idx': 1, 'z_divisor': 100, 'z_axis_name': "Preis (Euro)"}


def accumulate_sqlite(cursor: Cursor, start_station: int, end_station: int, timeframe_start: datetime,
                      timeframe_end: datetime, query_datatype: str, num_bins_per_day: int = 24 / 3) -> dict[
    str, list[tuple[int, int]]]:
    # Create a dictionary to store accumulated prices
    z_values = defaultdict(lambda: [])

    millis_per_bin = int(1000 * 60 * 60 * 24 / num_bins_per_day)
    query = f"""
    WITH RankedPrices AS (
    SELECT 
        `when`,
        `price_cents`,
        `travel_duration`,
        `queried_at`,
        `queried_at` / {millis_per_bin} as queried_at_bin,
        `when` / {millis_per_bin} as when_bin,
        ROW_NUMBER() OVER (PARTITION BY `queried_at` / {millis_per_bin}, `when` / {millis_per_bin} ORDER BY `price_cents` ASC) as rn
    FROM fahrpreise
    WHERE `from` = {start_station}
      AND `to` = {end_station}
      AND `price_cents` > 0
      AND `queried_at` >= {round(timeframe_start.timestamp() * 1000)}
      AND `queried_at` <= {round(timeframe_end.timestamp() * 1000)}
)
SELECT 
    `when`,
    `price_cents`,
    `travel_duration`,
    `queried_at`,
    queried_at_bin,
    when_bin
FROM RankedPrices
WHERE rn = 1;
    """

#     query = f"""
#     SELECT `when`,
#        min(`price_cents`),
#        `travel_duration`,
#        `queried_at`,
#        `queried_at` / {millis_per_bin} as queried_at_bin,
#        `when` / {millis_per_bin}       as when_bin
# FROM fahrpreise t1
# where `from` = {start_station}
#   and `to` = {end_station}
#   and `queried_at` >= {round(timeframe_start.timestamp() * 1000)}
#   and `queried_at` <= {round(timeframe_end.timestamp() * 1000)}
#   and  (SELECT id
#                      FROM fahrpreise t2
#                       where `from` = {start_station}
#                       and `to` = {end_station}
#                       and `queried_at` / {millis_per_bin}  = t1.`queried_at`  / {millis_per_bin}
#                       and `when` / {millis_per_bin}    = t1.`when` / {millis_per_bin}
#                       order by `price_cents`
#                       limit 1
#                      ) = t1.`id`
# group by `queried_at_bin`, `when_bin`
#                 """
    print(query)
    cursor.execute(query)

    # Fetch all rows and accumulate prices/durations
    rows = cursor.fetchall()
    for row in rows:
        when = row[5] * millis_per_bin  # use when_bin
        z = row[Query_Datatype[query_datatype].value['column_idx']]
        queried_at = row[3]
        z_values[when].append((int(queried_at), int(z)))

    return z_values


def open_sqlite(filename):
    conn = sqlite3.connect(filename)
    cursor = conn.cursor()
    return conn, cursor


def plot(result: Dict[str, List[tuple[int, int]]], x_day_range_past: int, x_day_range_future: int, query_datatype: str,
         num_bins_per_day: int = 24 / 3) -> Figure:
    """
    :param query_datatype: config for the query
    :param result: the data to ingest for the plot
    :param x_day_range_past: how many days before departure to display
    :param x_day_range_future: how many days after departure to display
    :param num_bins_per_day: how many prices to consider per day, should match the query interval (defaults to every 3 hours)
    """
    query_config = Query_Datatype[query_datatype]
    queried_at_num_bins = int((x_day_range_past + x_day_range_future) * num_bins_per_day)
    queried_at_departure_bin_index = queried_at_num_bins - int((x_day_range_future) * num_bins_per_day)
    zmap: Dict[datetime, List[float]] = defaultdict(lambda: [-1] * (queried_at_num_bins))

    for i, travelprices in enumerate(result.items()):
        try:
            when, price_records = travelprices
            starttime: datetime = datetime.fromtimestamp(int(when) / 1000)
            price_record: Dict[str, int]
            for queried_at, z in price_records:
                queried_at_date = datetime.fromtimestamp(queried_at / 1000)
                days_to_departure = (starttime - queried_at_date).total_seconds() / (60 * 60 * 24)
                queried_at_bin_index = queried_at_departure_bin_index - int(days_to_departure * num_bins_per_day)
                if queried_at_bin_index >= queried_at_num_bins or queried_at_bin_index < 0:
                    # discard datapoint because out of rendering range
                    continue
                try:
                    zmap[starttime][queried_at_bin_index] = z / query_config.value['z_divisor']
                except:
                    print(f"{queried_at_bin_index} {days_to_departure} {starttime} {queried_at_date}")
                    raise
        except:
            logging.exception("exception while prepping plot %d %s", i, travelprices)

    sorted_pricemap = sorted(zmap.items())
    fig = px.imshow([x[1] for x in sorted_pricemap],
                    labels=dict(x="tage bis abfahrt / wann ich buche", y="datum der reise / wann ich fahren möchte",
                                color=query_config.value['z_axis_name']),
                    x=[f"{-(x - queried_at_departure_bin_index) / num_bins_per_day:.2f}" for x in
                       range(int(queried_at_num_bins))],
                    y=[k.strftime('%A %d-%m-%Y, %H:%M') for k, v in sorted_pricemap]
                    )
    return fig


def get_timeframe(past, future):
    timeframe_start: datetime = datetime.now() - timedelta(days=past)
    timeframe_end: datetime = datetime.now() + timedelta(days=future)
    return timeframe_start, timeframe_end


def get_connection_tuples(cursor: Cursor) -> Generator[Tuple[Tuple[int, str], Tuple[int, str]], Any, None]:
    cursor.execute("select distinct `from`,`from_station`.`name`,`to`,`to_station`.`name` from fahrpreise "
                   "join `stations` as from_station , `stations` as `to_station` "
                   "where `from`=`from_station`.`number` and `to`=`to_station`.`number`;")
    return ((
        (int(row[0]), row[1]),
        (int(row[2]), row[3])
    ) for row in cursor.fetchall())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='accumulate fahrpreis data')
    parser.add_argument('--dbfile', help='path to the sqlitefile with the data', required=True)
    parser.add_argument('--output_file', help='if set, writes the html to the given file')
    parser.add_argument('--start_station', help='start station id', required=True)
    parser.add_argument('--end_station', help='end station id', required=True)
    parser.add_argument('--plot_timeframe_past', help='oldest travel start date on the plot, days relative to now',
                        default=60)
    parser.add_argument('--plot_timeframe_future', help='newest travel start date on the plot, days relative to now',
                        default=10)
    parser.add_argument('--plot_timeframe_date', help='what now is for timeframe',
                        default=datetime.now())

    args = parser.parse_args()
    timeframe_start, timeframe_end = get_timeframe(args.plot_timeframe_past, args.plot_timeframe_future)
    conn, cursor = open_sqlite(args.dbfile)
    result = accumulate_sqlite(cursor, int(args.start_station), int(args.end_station),
                               timeframe_start, timeframe_end,
                               Query_Datatype.price_cents.name)
    conn.close()
    figure = plot(result, 60, 1, Query_Datatype.price_cents.name)
    if args.output_file:
        html = figure.to_html()
        with open(args.output_file, "w") as text_file:
            text_file.write(html)
    else:
        figure.show()
