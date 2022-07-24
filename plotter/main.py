import functools
import json
import os
from datetime import datetime
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt

import brotli

import argparse
import matplotlib.dates as mdates

parser = argparse.ArgumentParser(description='accumulate fahrpreis data')
parser.add_argument('--accufile',
                    help='file with latest accu data (/tmp/fahrpreise_akku) usuful for working on plotting')
parser.add_argument('--datafolder',
                    help='data folder location',
                    default="/tmp/fahrpreise")
args = parser.parse_args()


def accumulate_data():
    result = {}
    with os.scandir(args.datafolder) as it:
        for entry in it:
            if entry.name.endswith('.brotli') and entry.is_file():
                try:
                    with open(entry, 'rb') as in_file:
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
                                if dict_key not in result:
                                    result[dict_key] = []
                                result[dict_key].append({"queried_at":queried_at,"price": price})

                except Exception as e:
                    print("Could not read file %s, %s" % (entry, e))
    return result

isoformatstr = "%Y-%m-%dT%H:%M:%S.%fZ"

def plot(result: Dict[str, List[Tuple[str, str]]]):
    time_to_departure = []
    booking_date = []
    departure_date = []
    y_axis2 = []
    travel_price = []
    z_axis2 = []
    for i, travelprices in enumerate(result.items()):
        keystr = travelprices[0]
        starttime = datetime.strptime(keystr.split("$")[1],isoformatstr)
        endtime = datetime.strptime(keystr.split("$")[3],isoformatstr)
        z_axis2.append((endtime-starttime).total_seconds())
        y_axis2.append(starttime)
        for data in travelprices[1]:
            time_to_departure.append(-(starttime - datetime.strptime(data["queried_at"], isoformatstr)).total_seconds()/(60*60*24))
            booking_date.append(datetime.strptime(data["queried_at"], isoformatstr))
            departure_date.append(starttime)
            travel_price.append(data["price"])

    color_map = plt.cm.plasma
    plt.rcParams['figure.figsize'] = [30, 50]
    fig, ax = plt.subplots(1)
    prices = ax
    #plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%a %d.%m'))
    plt.gca().yaxis.set_major_formatter(mdates.DateFormatter('%a %d.%m'))
    #plt.gca().xaxis.set_major_locator(mdates.DayLocator())
    plt.gca().yaxis.set_major_locator(mdates.DayLocator())
    pcm = prices.scatter(time_to_departure, departure_date, c=travel_price, cmap=color_map, marker=".", s=1,vmax=75)
    #fig.autofmt_xdate()
    #prices.twinx().barh(y_axis2,z_axis2,height=0.1)
    fig.colorbar(pcm,label="price",ax=prices)
    plt.gca().xaxis.set_label_text("tage bis abfahrt / wann ich buche")
    plt.gca().yaxis.set_label_text("datum der reise / wann ich fahren möchte")
    plt.show()


result = {}
if args.accufile:
    print("reading data from tmpfile")
    with open(args.accufile, "r") as infile:
        result = json.load(infile)
else:
    result = accumulate_data()
    with open("/tmp/fahrpreise_akku", "w") as outfile:
        json.dump(result, outfile)
        print("wrote accufile")

plot(result)
