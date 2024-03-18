You can install the gatherer to a linux host with ansible with this role.

After running this role, write your stations seperated by `;` , one at each line into `/opt/fahrpreis_gatherer/stations.csv`
The gatherer runs as a systemd timer every 3 hours and writes the results to the configured sqlite file
