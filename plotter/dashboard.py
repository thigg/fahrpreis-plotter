import argparse
import json

import dash
from dash import dcc, html
from dash.dependencies import Input, Output
from flask_caching import Cache

from plotter import accumulate_sqlite, plot, get_timeframe, open_sqlite, get_connection_tuples,Query_Datatype

dbfilepath=""

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='accumulate fahrpreis data')
    parser.add_argument('--dbfile', help='path to the sqlitefile with the data', required=True)
    parser.add_argument('--port', help='server port', required=True)
    args = parser.parse_args()
    dbfilepath = args.dbfile
else:
    # Opening JSON file
    f = open('/etc/fahrpreis-plotter-config.json')

    # returns JSON object as
    # a dictionary
    data = json.load(f)
    dbfilepath=data['dbfile']

app = dash.Dash(__name__)
cache = Cache(app.server, config={
    'CACHE_TYPE': 'filesystem',
    'CACHE_DIR': '/tmp/fahrpreise-cache'
})
app.config.suppress_callback_exceptions = True
app.layout = html.Div([
dcc.Interval(
    id="load_interval",
    n_intervals=0,
    max_intervals=1, #<-- only run once
    interval=1
),
    html.Div([
        html.Label("Select Connection:"),
        dcc.Dropdown(id='connection-input', clearable=False),
        html.Label("Query:"),
        dcc.Dropdown(id='query-input', options=[{'label': i.name, 'value': i.name} for i in Query_Datatype],
                     value="price_cents"),
    ], style={'width': '20em', 'display': 'inline-block'}),
    dcc.Graph(id='output-plot', style={'height': '100vh', 'flex-grow': '1'})
], style={'height': '100vh', 'display': 'flex'})

@app.callback(
    Output('connection-input', 'options'),
    Output('connection-input', 'value'),
    [Input('load_interval', 'n_intervals')]
)
@cache.memoize(timeout=60*60)
def update_connection_options(ignore):
    print("querying connections")
    conn, cursor = open_sqlite(dbfilepath)
    connections = [x for x in get_connection_tuples(cursor)]
    conn.close()
    return [{'label': f"{x[0][1]}-{x[1][1]}", 'value': f"{x[0][0]}-{x[1][0]}"} for x in
                                          connections], f"{connections[0][0][0]}-{connections[0][1][0]}"


@app.callback(
    Output('output-plot', 'figure'),
    [Input('connection-input', 'value'),
        Input('query-input', 'value')
     ]
)
@cache.memoize(timeout=60*60)
def update_plot(connection,query):
    print(f"rendering connection {connection}")
    conn, cursor = open_sqlite(dbfilepath)

    station1, station2 = connection.split("-")
    timeframe_start, timeframe_end = get_timeframe(60, 10)

    result = accumulate_sqlite(cursor, station1, station2, timeframe_start, timeframe_end,query)
    conn.close()
    return plot(result, 60, 1, query)


# Run the Dash app
if __name__ == '__main__':
    app.run(port=args.port)
