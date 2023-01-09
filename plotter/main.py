import argparse
import functools
import itertools
import json
import logging
import lzma
import os
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

import brotli
import matplotlib.dates as mdates
import matplotlib.pyplot as plt

parser = argparse.ArgumentParser(description='accumulate fahrpreis data')
parser.add_argument('--accufile',
                    help='file with latest accu data (/tmp/fahrpreise_akku) usefull for working on plotting')
parser.add_argument('start_station',
                    help='start station id')
parser.add_argument('end_station', help='end station id')
parser.add_argument('--plot_timeframe_past', help='oldest travel start date on the plot, days relative to now',
                    default=60)
parser.add_argument('--plot_timeframe_future', help='newest travel start date on the plot, days relative to now',
                    default=10)

args = parser.parse_args()


def handle_file(path: str):
    """
    reads a record from the crawler and transofrms it into a list with connections and prices
    :param path: the file to read
    :return: a list of connections with prices and when the price was queried
    """
    try:
        result = list()
        with open(path, 'rb') as in_file:
            decompressor = brotli.Decompressor()
            s: str = ''
            read_chunk = functools.partial(in_file.read, )
            for data in iter(read_chunk, b''):
                s += bytes.decode(decompressor.process(data), 'utf-8')
            dict = json.loads(s)
            queried_at = dict['queried_at']
            for day in dict['data']:
                for travel in day:
                    price = travel['price']['amount']
                    start_station = travel['legs'][0]['origin']['id']
                    start_time = travel['legs'][0]['departure']
                    end_station = travel['legs'][-1]['origin']['id']
                    end_time = travel['legs'][-1]['departure']
                    dict_key = "$".join([start_station, start_time, end_station, end_time])
                    result.append((dict_key, {"queried_at": queried_at, "price": price}))
        return result
    except Exception as e:
        print("Could not read file %s, %s, size: %d" % (path, e, os.stat(path).st_size))
    return []


def accumulate_data() -> dict[str, list[dict[str, object]]]:
    """
    preprocesses the raw data into the data we need for the plot
    :return: a dictionary of all travels (a connection at a specific datetime) with a list of prices and when the price was queried
    """
    starttime = datetime.now()
    result: dict[str, list[dict[str, object]]] = defaultdict(list)
    with os.scandir("/tmp/fahrpreise/") as dirIterator:
        with ProcessPoolExecutor() as executor:
            resultlist = list(
                itertools.chain.from_iterable(
                    executor.map(handle_file, (str(entry.path) for entry in dirIterator if
                                               entry.name.endswith('.brotli') and entry.is_file()))))
            print(f"got resultlist {len(resultlist)}")
            for item in resultlist:
                if item:
                    key, value = item
                    result[key].append(value)

    print(f"accumulation took {datetime.now() - starttime}")
    return result


isoformatstr = "%Y-%m-%dT%H:%M:%S.%fZ"


def plot(result: Dict[str, List[Tuple[str, str]]], start_station_filter: str, end_station_filter: str,
         starttime_after: datetime, starttime_before):
    """

    :param result: the data to ingest for the plot
    :param start_station_filter: which start station to consider
    :param end_station_filter: which end station to consider
    :param starttime_after: timeframe to plot lower limit
    :param starttime_before: timeframe to plot upper limit
    :return: shows the plot
    """
    print(f"creating filtered plot for stations: {start_station_filter}, {end_station_filter}")
    time_to_departure = []
    # booking_date = []
    departure_date = []
    # y_axis2 = []
    travel_price = []
    # z_axis2 = []
    recorded_connections: dict[tuple[str, str], int] = defaultdict(lambda: 0)
    for i, travelprices in enumerate(result.items()):
        try:
            keystr = travelprices[0]
            keystr_split = keystr.split("$")
            start_station = keystr_split[0]
            end_station = keystr_split[2]
            recorded_connections[(start_station, end_station)] += 1
            if start_station != start_station_filter or end_station != end_station_filter:
                # print(f"skipping '{start_station}'({type(start_station)}) '{end_station}' because filters '{start_station_filter}'({type(start_station_filter)}) '{end_station_filter}'")
                continue
            starttime = datetime.strptime(keystr_split[1], isoformatstr)
            endtime = datetime.strptime(keystr_split[3], isoformatstr)
            # z_axis2.append((endtime-starttime).total_seconds())
            # y_axis2.append(starttime)
            for data in travelprices[1]:
                if starttime > starttime_after and starttime < starttime_before:
                    time_to_departure.append(
                        -(starttime - datetime.strptime(data["queried_at"], isoformatstr)).total_seconds() / (
                                60 * 60 * 24))
                    # booking_date.append(datetime.strptime(data["queried_at"], isoformatstr))
                    departure_date.append(starttime)
                    travel_price.append(data["price"])
        except:
            logging.exception("exception while prepping plot %d %s", i, travelprices)
    print("recorded connections: " + str(recorded_connections.items()))
    print("resulting datapoints: %d" % len(travel_price))
    print("resulting datapoints for filter: %d" % recorded_connections[(start_station_filter, end_station_filter)])
    color_map = plt.cm.plasma
    plt.rcParams['figure.figsize'] = [30, 50]
    fig, ax = plt.subplots(1)
    prices = ax
    # plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%a %d.%m'))
    plt.gca().yaxis.set_major_formatter(mdates.DateFormatter('%a %d.%m'))
    # plt.gca().xaxis.set_major_locator(mdates.DayLocator())
    plt.gca().yaxis.set_major_locator(mdates.DayLocator())
    pcm = prices.scatter(time_to_departure, departure_date, c=travel_price, cmap=color_map, marker=".", s=1, vmax=75)
    # fig.autofmt_xdate()
    # prices.twinx().barh(y_axis2,z_axis2,height=0.1)
    fig.colorbar(pcm, label="price", ax=prices)
    plt.gca().xaxis.set_label_text("tage bis abfahrt / wann ich buche")
    plt.gca().yaxis.set_label_text("datum der reise / wann ich fahren möchte")
    plt.show()


result = {}
if args.accufile:
    print("reading data from tmpfile")
    with lzma.open(args.accufile, "rt") as infile:
        result = json.load(infile)
        print("done reading infile")
else:
    starttime = datetime.now()
    result = accumulate_data()
    startcompresstime = datetime.now()
    with lzma.open("/tmp/fahrpreise_akku", "wt", preset=4) as outfile:
        print("writing accufile")
        json.dump(result, outfile)
        print(
            f"wrote accufile. whole process took total={datetime.now() - starttime} akku={startcompresstime - starttime} write={datetime.now() - startcompresstime}")

plot(result, args.start_station, args.end_station, datetime.now() - timedelta(days=args.plot_timeframe_past),
     datetime.now() + timedelta(days=args.plot_timeframe_future))
