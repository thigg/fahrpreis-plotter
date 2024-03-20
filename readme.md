# fahrpreis statistiken

Collect connection prices (fahrpreise) of the Deutsche Bahn every couple hours,
to see how connection prices change over time.
Includes a tool for plotting them as well!

It is a tool you can run to gather every vew hours prices for a connection you specified.
Those prices can then be plotted to see how connection prices change over time.

## Result
These are the prices I collected for a connection I was interested in.
 - X-axis is the price until departure
 - Y-axis the date until departure.

Findings:
 - the vetical line at ~4 weeks before departure shows a discontinuity
 - some connections (especially weekends/holidays) are always expensive

![fahpreise plot](images/img.png)

## How to run
I run the service on a server and create the plots from my laptop. I sync the database file to my laptop for plotting.
### install gatherer service
You can install the gatherer via ansible using this [role](./gatherer_role).
This sets the [node app](./gatherer_hafas) up as a separate user and adds a systemd service and timer
### plot
 1. get the file
 2. run `plotter/main.py` (install dependencies before?) with required arguments

# Contributing
For questions/issues use the issue tracker. Feel free to create pull requests with your modifications.

If you created interesting results with this tool and published them, let me know, I'll add you to the readme page.


# License
This was based on [db-prices-cli](https://github.com/derhuerst/db-prices-cli)
and by Jannis R. Thanks go to him for the great base.

Reworked this to work with a fork of [hafas-client](https://github.com/public-transport/hafas-client). thanks to the authos

See the [license file](license.md) for further information.
