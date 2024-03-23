import argparse
import logging
import sqlite3
from collections import defaultdict
from datetime import datetime, timedelta
from sqlite3 import Cursor
from typing import Dict, List, Tuple, Generator, Any

import plotly.express as px
from plotly.graph_objs import Figure



def accumulate_sqlite(cursor: Cursor, start_station: int, end_station: int, timeframe_start: datetime,
                      timeframe_end: datetime) -> dict[str, list[tuple[int, int]]]:

    # Create a dictionary to store accumulated prices
    prices_dict = defaultdict(lambda: [])

    # Execute SQL query to fetch data from the table
    cursor.execute("SELECT `when`, `price_cents`, `queried_at` FROM fahrpreise "
                   f"where `from` = {start_station} and `to` = {end_station} "
                   f"and `queried_at` >= {round(timeframe_start.timestamp() * 1000)} "
                   f"and `queried_at` <= {round(timeframe_end.timestamp() * 1000)}")

    # Fetch all rows and accumulate prices
    rows = cursor.fetchall()
    for row in rows:
        when = row[0]
        price = row[1]
        queried_at = row[2]
        prices_dict[when].append((int(queried_at), int(price)))

    return prices_dict


def open_sqlite(filename):
    conn = sqlite3.connect(filename)
    cursor = conn.cursor()
    return conn, cursor


def plot(result: Dict[str, List[tuple[int, int]]], x_day_range_past: int, x_day_range_future: int, num_bins_per_day: int = 24 / 3) -> Figure:
    """
    :param result: the data to ingest for the plot
    :param x_day_range_past: how many days before departure to display
    :param x_day_range_future: how many days after departure to display
    :param num_bins_per_day: how many prices to consider per day, should match the query interval (defaults to every 3 hours)
    """
    queried_at_num_bins = int((x_day_range_past+x_day_range_future) * num_bins_per_day)
    queried_at_departure_bin_index = queried_at_num_bins - int((x_day_range_future) * num_bins_per_day)
    pricemap: Dict[datetime, List[float]] = defaultdict(lambda: [-1] * (queried_at_num_bins))

    for i, travelprices in enumerate(result.items()):
        try:
            when, price_records = travelprices
            starttime: datetime = datetime.fromtimestamp(int(when) / 1000)
            price_record: Dict[str, int]
            for queried_at, price in price_records:
                queried_at_date = datetime.fromtimestamp(queried_at / 1000)
                days_to_departure = (starttime - queried_at_date).total_seconds() / (60 * 60 * 24)
                queried_at_bin_index = queried_at_departure_bin_index - int(days_to_departure * num_bins_per_day)
                if queried_at_bin_index >= queried_at_num_bins or queried_at_bin_index < 0:
                    # discard datapoint because out of rendering range
                    continue
                try:
                    pricemap[starttime][queried_at_bin_index] = price / 100
                except:
                    print(f"{queried_at_bin_index} {days_to_departure} {starttime} {queried_at_date}")
                    raise
        except:
            logging.exception("exception while prepping plot %d %s", i, travelprices)

    sorted_pricemap = sorted(pricemap.items())
    fig = px.imshow([x[1] for x in sorted_pricemap],
                    labels=dict(x="tage bis abfahrt / wann ich buche", y="datum der reise / wann ich fahren möchte",
                                color="Preis (Euro)"),
                    x=[f"{-(x-queried_at_departure_bin_index) / num_bins_per_day:.2f}" for x in range(int(queried_at_num_bins))],
                    y=[k.strftime('%A %d-%m-%Y, %H:%M') for k, v in sorted_pricemap]
                    )
    return fig


def get_timeframe(past, future):
    timeframe_start: datetime = datetime.now() - timedelta(days=past)
    timeframe_end: datetime = datetime.now() + timedelta(days=future)
    return timeframe_start, timeframe_end

def get_connection_tuples(cursor:Cursor)->Generator[Tuple[Tuple[int,str],Tuple[int,str]], Any,None]:
    cursor.execute("select distinct `from`,`from_station`.`name`,`to`,`to_station`.`name` from fahrpreise "
                   "join `stations` as from_station , `stations` as `to_station` "
                   "where `from`=`from_station`.`number` and `to`=`to_station`.`number`;")
    return ((
        (int(row[0]),row[1]),
        (int(row[2]),row[3])
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
    timeframe_start, timeframe_end = get_timeframe(args.plot_timeframe_past,args.plot_timeframe_future)
    conn, cursor = open_sqlite(args.dbfile)
    result = accumulate_sqlite(cursor, int(args.start_station), int(args.end_station), timeframe_start, timeframe_end)
    conn.close()
    figure = plot(result, 60, 1)
    if args.output_file:
        html = figure.to_html()
        with open(args.output_file, "w") as text_file:
            text_file.write(html)
    else:
        figure.show()
