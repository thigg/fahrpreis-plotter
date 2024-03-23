import argparse

import dash
from dash import dcc, html
from dash.dependencies import Input, Output

from plotter import accumulate_sqlite, plot, get_timeframe, open_sqlite, get_connection_tuples

app = dash.Dash(__name__)



# Define the callback function
@app.callback(
    Output('output-plot', 'figure'),
    [Input('x-input', 'value')]
)
def update_plot(x):
    conn, cursor = open_sqlite("/tmp/fahrpreise.sqlite3")

    station1, station2 = x.split("-")
    timeframe_start, timeframe_end = get_timeframe(60, 10)

    result = accumulate_sqlite(cursor, station1, station2, timeframe_start, timeframe_end)
    conn.close()
    return plot(result, 60, 1)


# Run the Dash app
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='accumulate fahrpreis data')
    parser.add_argument('--dbfile', help='path to the sqlitefile with the data', required=True)
    args = parser.parse_args()
    conn, cursor = open_sqlite(args.dbfile)
    connections = [x for x in get_connection_tuples(cursor)]
    conn.close()
    # Define the layout
    app.layout = html.Div([
        html.Div([
            html.Label("Select Connection:"),
            dcc.Dropdown(id='x-input', clearable=False,
                         options=[{'label': f"{x[0][1]}-{x[1][1]}", 'value': f"{x[0][0]}-{x[1][0]}"} for x in
                                  connections],
                         value=f"{connections[0][0][0]}-{connections[0][1][0]}"),
            # html.Label("Select Y value:"),
            # dcc.Dropdown(id='y-input', options=[{'label': i, 'value': i} for i in connections], value=connections[1]),
        ], style={'width': '100%', 'display': 'inline-block'}),
        dcc.Graph(id='output-plot', style={'height': 'calc(100vh - 150px)'})
    ], style={'height': '100vh'})

    app.run_server(debug=True)
