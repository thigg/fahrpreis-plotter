import argparse
import logging
import sqlite3
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List

import plotly.express as px
from plotly.graph_objs import Figure

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


def accumulate_sqlite(filename: str, start_station: int, end_station: int, timeframe_start: datetime,
                      timeframe_end: datetime) -> dict[str, list[tuple[int, int]]]:
    conn = sqlite3.connect(filename)
    cursor = conn.cursor()

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

    conn.close()
    return prices_dict


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


timeframe_start: datetime = datetime.now() - timedelta(days=args.plot_timeframe_past)
timeframe_end: datetime = datetime.now() + timedelta(days=args.plot_timeframe_future)
result = accumulate_sqlite(args.dbfile, int(args.start_station), int(args.end_station), timeframe_start, timeframe_end)
figure = plot(result, 60, 1)
if args.output_file:
    html = figure.to_html()
    with open(args.output_file, "w") as text_file:
        text_file.write(html)
else:
    figure.show()
