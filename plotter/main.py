import argparse
import logging
import sqlite3
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List

import matplotlib.dates as mdates
import matplotlib.pyplot as plt

parser = argparse.ArgumentParser(description='accumulate fahrpreis data')
parser.add_argument('--dbfile', help='path to the sqlitefile with the data', required=True)
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


def plot(result: Dict[str, List[tuple[int, int]]]):
    """

    :param result: the data to ingest for the plot
    :return: shows the plot
    """
    time_to_departure = []
    # booking_date = []
    departure_date = []
    # y_axis2 = []
    travel_price_euro = []
    # z_axis2 = []
    for i, travelprices in enumerate(result.items()):
        try:
            when, price_records = travelprices
            starttime = datetime.fromtimestamp(int(when) / 1000)
            # z_axis2.append((endtime-starttime).total_seconds())
            # y_axis2.append(starttime)
            price_record: Dict[str, int]
            for queried_at, price in price_records:
                queried_at_date = datetime.fromtimestamp(queried_at / 1000)
                days_to_departure = (starttime - queried_at_date).total_seconds() / (60 * 60 * 24)
                time_to_departure.append(-days_to_departure)
                departure_date.append(starttime)
                travel_price_euro.append(price / 100)
        except:
            logging.exception("exception while prepping plot %d %s", i, travelprices)
    print("resulting datapoints: %d" % len(travel_price_euro))
    plt.rcParams['figure.figsize'] = [12, 20]
    fig, ax = plt.subplots(1)
    price_records = ax
    # plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%a %d.%m'))
    plt.gca().yaxis.set_major_formatter(mdates.DateFormatter('%a %d.%m'))
    # plt.gca().xaxis.set_major_locator(mdates.DayLocator())
    plt.gca().yaxis.set_major_locator(mdates.DayLocator())
    pcm = price_records.scatter(time_to_departure, departure_date, c=travel_price_euro, cmap=plt.colormaps["plasma"], marker=".", s=1,
                                vmax=75)
    # fig.autofmt_xdate()
    # prices.twinx().barh(y_axis2,z_axis2,height=0.1)
    fig.colorbar(pcm, label="price (Euro)", ax=price_records)
    plt.gca().xaxis.set_label_text("tage bis abfahrt / wann ich buche")
    plt.gca().yaxis.set_label_text("datum der reise / wann ich fahren möchte")
    plt.show()


timeframe_start: datetime = datetime.now() - timedelta(days=args.plot_timeframe_past)
timeframe_end: datetime = datetime.now() + timedelta(days=args.plot_timeframe_future)
result = accumulate_sqlite(args.dbfile, int(args.start_station), int(args.end_station), timeframe_start, timeframe_end)
plot(result)
