import dash
import dash_core_components as dcc
import dash_html_components as html
import geopandas as gpd
import plotly.graph_objects as go
from dash.dependencies import Input, Output

df = gpd.read_file('extents_4326_simple.gpkg')
df.duration = (df.duration / 3600).astype(int)


external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

children = [html.H1(children=''),  html.Div(children='')]

e = df[(df.threshold == df.threshold[0]) & (df.run_id == df.run_id[0])]

building_depths = gpd.read_file('building_depths_with_green_areas_thresholded_4326.gpkg')

layout = go.Layout(
    hovermode='closest',
    margin=go.layout.Margin(l=0, r=0, b=0, t=0),
    mapbox_style="basic",
    uirevision=True,
    mapbox_accesstoken='pk.eyJ1IjoiZm1jY2xlYW4iLCJhIjoiY2swbWpkcXY2MTRhNTNjcHBvM3R2Z2J6MiJ9.zOehGKT1N3eask9zsKmQqA',
    mapbox=go.layout.Mapbox(
        center=go.layout.mapbox.Center(
            lat=e.geometry.centroid.y.mean(),
            lon=e.geometry.centroid.x.mean()
        ),
        zoom=10
    )
)
fig = go.Figure(go.Choroplethmapbox(), layout)

graph = dcc.Graph(
    id='map',
    figure=fig,
    clear_on_unhover=True,
    style={
        'zIndex': -1}
)


thresholds = df.threshold.unique()
rainfall = df.rainfall.unique()
duration = df.duration.unique()
threshold_marks = {key: str(val) for key, val in enumerate(thresholds)}
rainfall_marks = {key: str(val) for key, val in enumerate(rainfall)}
duration_marks = {key: str(val) for key, val in enumerate(duration)}


def create_slider(title, name, marks):
    return html.Div(
        children=[
            title,
            dcc.Slider(
                id=name,
                min=0,
                max=len(marks)-1,
                marks=marks,
                value=0,
                updatemode='drag'
            )
        ],
        style={'margin': 40}
    )


slider = create_slider('Depth Threshold (m)', 'threshold-slider', threshold_marks)
rainfall_slider = create_slider('Rainfall Amount (mm)', 'rainfall-slider', rainfall_marks)
duration_slider = create_slider('Rainfall Duration (hrs)', 'duration-slider', marks=duration_marks)

green_areas = dcc.Checklist(id='green-areas', options=[{'label': 'Green Areas', 'value': '-'}])
green_areas_div = html.Div(green_areas, style={'margin': 10, 'textAlign': 'center', 'display': 'inline-block'})

density = dcc.Checklist(id='density', options=[{'label': 'Show heat-map', 'value': '-'}])
density_div = html.Div(density,  style={'margin': 10, 'textAlign': 'center', 'display': 'inline-block'})

buildings = dcc.Checklist(id='buildings', options=[{'label': 'Show building depths', 'value': '-'}])
buildings_div = html.Div(buildings, style={'margin': 10, 'textAlign': 'center', 'display': 'inline-block'})

basemap_dropdown = html.Div(children=[

    html.P('Base Map: '),
    dcc.Dropdown(
        id='basemap',
        options=[
            {
                'label': s.title().replace('-', ' '), 'value': s} for s in
            [
                "basic",
                "streets",
                "outdoors",
                "light",
                "dark",
                "satellite",
                "satellite-streets",
                "open-street-map",
                "carto-positron",
                "carto-darkmatter",
                "stamen-terrain",
                "stamen-toner",
                "stamen-watercolor"
            ]
        ],
        value='basic', style={'width': 200, 'margin': 10}),

], style={'display': 'inline-block'})

slider_div = html.Div(children=[slider, rainfall_slider, duration_slider,
                                html.Div(children=[green_areas_div, density_div, buildings_div, basemap_dropdown],
                                         style={'textAlign': 'center'})],
                      style={'margin': 50, })

children.append(slider_div)
children.append(graph)
children.append(html.Div(id='layout', children=['']))

app.layout = html.Div(children=children)


@app.callback(Output(component_id='map', component_property='figure'),
              [Input(component_id='threshold-slider', component_property='value'),
               Input(component_id='rainfall-slider', component_property='value'),
               Input(component_id='duration-slider', component_property='value'),
              Input(component_id='green-areas', component_property='value'),
               Input(component_id='basemap', component_property='value'),
               Input(component_id='density', component_property='value'),
               Input(component_id='buildings', component_property='value'),
               ])
def update_plot(threshold, rain, dur, green, bm, dens, build):
    if threshold is not None and rain is not None and dur is not None:

        green = 1 if green else 0

        features = df[(df.threshold == float(threshold_marks[threshold])) &
                      (df.rainfall == float(rainfall_marks[rain])) &
                      (df.duration == float(duration_marks[dur])) &
                      (df.green == green)]

        traces = list()

        traces.append(
            go.Choroplethmapbox(geojson=features.__geo_interface__,
                                locations=features.index,
                                z=features.threshold,
                                showscale=False,
                                colorscale=[[0, 'royalblue'], [1, 'royalblue']],
                                marker=dict(opacity=0.5),
                                hoverinfo='skip',
                                below=''
                                ))
        if build or dens:
            thresh = float(threshold_marks[threshold])
            depth_values = building_depths['max_depth_{}'.format(features.run_id.iloc[0])]
            buildings_above_threshold = building_depths[depth_values >= thresh]

            if build:

                t = go.Choroplethmapbox(
                    geojson=buildings_above_threshold.__geo_interface__,
                    locations=buildings_above_threshold.index,
                    z=depth_values[depth_values >= thresh],
                    below=''
                )
                traces.append(t)
            else:
                traces.append(go.Choroplethmapbox())

            if dens:
                traces.append(go.Densitymapbox(lat=buildings_above_threshold.y,
                                               lon=buildings_above_threshold.x,
                                               z=depth_values[depth_values >= thresh],
                                               radius=10,
                                               hoverinfo='skip',
                                               showscale=True if not build else False
                                               ))
            else:
                traces.append(go.Densitymapbox())

        return go.Figure(traces, layout.update(mapbox_style=bm))
    else:
        return fig

@app.callback(Output('layout', 'children'),
              [Input('map', 'relayoutData')])
def show_layout(lay):
    if lay is not None:
        if 'mapbox.zoom' in lay:
            return [str(lay['mapbox.zoom'])]
        else:
            return []


if __name__ == '__main__':
    app.run_server(debug=True, port=8899, host='0.0.0.0')
