# ==============================================================================
# app.py — Dashboard MIRTI — República Dominicana (v3)
# ==============================================================================

import dash
from dash import dcc, html, Input, Output, dash_table
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import geopandas as gpd
import json
from pathlib import Path

# ==============================================================================
# 1. RUTAS Y CARGA DE DATOS
# ==============================================================================
data_dir = Path(__file__).parent / "data"

with open(data_dir / "municipios_rd.geojson", encoding="utf-8") as f:
    geojson_municipios = json.load(f)

with open(data_dir / "regiones_rd.geojson", encoding="utf-8") as f:
    geojson_regiones = json.load(f)

est_municipal    = pd.read_csv(data_dir / "est_municipal.csv")
genero_df        = pd.read_csv(data_dir / "genero_municipal.csv")
df_socio         = pd.read_csv(data_dir / "resumen_socioeconomico.csv")

est_municipal['ubigeo'] = est_municipal['ubigeo'].astype(str).str.zfill(4)
genero_df['ubigeo']     = genero_df['ubigeo'].astype(str).str.zfill(4)
est_municipal['categoria'] = est_municipal['categoria'].astype(str)

# Cargar agrupamiento regional
df_regional = pd.read_csv(data_dir / "agrupamiento_municipios_por_region.csv")
df_regional['ubigeo'] = df_regional['ubigeo'].astype(str).str.zfill(4)
df_regional = df_regional[['ubigeo', 'categoria_regional', 'categoria_detallada']]

gdf = gpd.read_file(data_dir / "municipios_rd.geojson")
gdf['ubigeo'] = gdf['ubigeo'].astype(str).str.zfill(4)

gdf_reg = gpd.read_file(data_dir / "regiones_rd.geojson")
gdf_reg['region'] = gdf_reg['cod_reg'].astype(int)
nombres_reg = dict(zip(gdf_reg['region'], gdf_reg['name_es']))

nombres_mun  = gdf[['ubigeo', 'name_en']].copy()
df_completo  = est_municipal.merge(genero_df,    on=['ubigeo', 'region'], how='left')
df_completo  = df_completo.merge(nombres_mun,    on='ubigeo',             how='left')
df_completo  = df_completo.merge(df_regional,    on='ubigeo',             how='left')

regiones = sorted(est_municipal['region'].unique())

print("✓ Datos cargados")

# ==============================================================================
# 2. CONSTANTES
# ==============================================================================
VERDE        = "#00542A"
ORDEN_CAT    = ['Muy baja', 'Baja', 'Media', 'Alta', 'Muy alta']
COLORES_CAT  = {
    'Muy baja': '#fde725',
    'Baja':     '#35b779',
    'Media':    '#31688e',
    'Alta':     '#443983',
    'Muy alta': '#440154',
    'Sin datos':'#cccccc'
}
ORDEN_CAT_REG   = ['Bajo', 'Medio', 'Alto']
COLORES_CAT_REG = {
    'Bajo':  '#fde725',
    'Medio': '#31688e',
    'Alto':  '#440154',
}

min_prev  = est_municipal['ti_pred_mean'].min()
max_prev  = est_municipal['ti_pred_mean'].max()
amplitud  = (max_prev - min_prev) / 5
limites   = [min_prev + i * amplitud for i in range(6)]

opciones_region = (
    [{'label': 'Todas las regiones', 'value': 0}] +
    [{'label': f"{nombres_reg.get(r, r)}", 'value': r} for r in regiones]
)

opciones_municipio = [
    {'label': row['name_en'], 'value': row['ubigeo']}
    for _, row in df_completo.sort_values('name_en').iterrows()
]

# ==============================================================================
# 3. APP
# ==============================================================================
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.FLATLY],
    title="MIRTI — República Dominicana"
)
server = app.server

# ==============================================================================
# 4. HELPERS
# ==============================================================================
def filtrar(region):
    if region == 0:
        return df_completo.copy()
    return df_completo[df_completo['region'] == region].copy()

def make_mapa(df_f, tipo='coropletico', variable='total', regional=False):
    col       = {'total': 'ti_pred_mean', 'hombre': 'prev_hombre', 'mujer': 'prev_mujer'}[variable]
    col_cat   = 'categoria_regional' if regional else 'categoria'
    colores   = COLORES_CAT_REG if regional else COLORES_CAT
    orden_cat = ORDEN_CAT_REG   if regional else ORDEN_CAT
    gdf_f     = gdf[gdf['ubigeo'].isin(df_f['ubigeo'])]
    clat      = gdf_f.geometry.centroid.y.mean()
    clon      = gdf_f.geometry.centroid.x.mean()

    if tipo == 'coropletico':
        fig = px.choropleth_mapbox(
            df_f, geojson=geojson_municipios,
            locations='ubigeo', featureidkey='properties.ubigeo',
            color=col_cat,
            color_discrete_map=colores,
            category_orders={col_cat: orden_cat},
            mapbox_style='carto-positron', zoom=6.5,
            center={"lat": clat, "lon": clon}, opacity=0.85,
            hover_name='name_en',
            hover_data={col: ':.1%', col_cat: True, 'n': True, 'ubigeo': True},
            labels={col: 'Prevalencia', col_cat: 'Nivel', 'n': 'Niños/as', 'ubigeo': 'Código'}
        )
    else:
        df_b = df_f.merge(gdf[['ubigeo','centroid_x','centroid_y']], on='ubigeo', how='left')
        fig = px.scatter_mapbox(
            df_b, lat='centroid_y', lon='centroid_x',
            size='n', color=col_cat,
            color_discrete_map=colores,
            category_orders={col_cat: orden_cat},
            mapbox_style='carto-positron', zoom=6.5,
            center={"lat": clat, "lon": clon},
            hover_name='name_en',
            hover_data={col: ':.1%', 'n': True},
            labels={col: 'Prevalencia', 'n': 'Niños/as'}
        )
    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0},
                      legend=dict(title="Nivel de riesgo",
                                  bgcolor="rgba(255,255,255,0.85)",
                                  bordercolor="#ddd", borderwidth=1))
    return fig

def kpi_card(titulo, id_val, color):
    return dbc.Card([dbc.CardBody([
        html.P(titulo, className="small text-muted mb-1"),
        html.H5(id=id_val, className="mb-0 fw-bold", style={"color": color})
    ])])

# ==============================================================================
# 5. LAYOUT
# ==============================================================================
HEADER = dbc.Navbar(
    dbc.Container([
        html.Div([
            html.H5("MIRTI — Modelo de Identificación del Riesgo de Trabajo Infantil · República Dominicana",
                    className="text-white mb-0 fw-bold"),
        ])
    ], fluid=True),
    color=VERDE, dark=True, className="py-2 mb-0"
)

FILTROS = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.Label("Región", className="small fw-bold text-muted mb-1"),
            dcc.Dropdown(id='dd-region', options=opciones_region,
                         value=0, clearable=False)
        ], width=3),
        dbc.Col([
            html.Label("Tipo de mapa", className="small fw-bold text-muted mb-1"),
            dcc.RadioItems(id='rd-mapa',
                options=[{'label': 'Mapa de riesgo', 'value': 'coropletico'},
                         {'label': 'Mapa de población',    'value': 'burbujas'}],
                value='coropletico', inline=True,
                inputStyle={"marginRight": "5px", "marginLeft": "12px"})
        ], width=3, className="d-flex align-items-end pb-1"),
    ], className="g-2")
], fluid=True, className="bg-light border-bottom py-2 mb-0")

TABS = dbc.Tabs([

    # ── Tab 1: Resumen nacional ───────────────────────────────────────────────
    dbc.Tab(label="Resumen nacional", tab_id="tab-resumen", children=[
        dbc.Container([
            dbc.Row([
                dbc.Col(dbc.Card([dbc.CardBody([
                    html.P("Prevalencia", className="small text-muted mb-1"),
                    html.H5(id='kpi-prev', className="mb-0 text-primary fw-bold")
                ])]),),
                dbc.Col(dbc.Card([dbc.CardBody([
                    html.P("Niños", className="small text-muted mb-1"),
                    html.H5(id='kpi-ninos', className="mb-0 fw-bold", style={"color":"#378ADD"})
                ])]),),
                dbc.Col(dbc.Card([dbc.CardBody([
                    html.P("Niñas", className="small text-muted mb-1"),
                    html.H5(id='kpi-ninas', className="mb-0 fw-bold", style={"color":"#D4537E"})
                ])]),),
                dbc.Col(dbc.Card([dbc.CardBody([
                    html.P("Muy alta", className="small text-muted mb-1"),
                    html.H5(id='kpi-muyalta', className="mb-0 fw-bold", style={"color":"#440154"})
                ])]),),
                dbc.Col(dbc.Card([dbc.CardBody([
                    html.P("Alta", className="small text-muted mb-1"),
                    html.H5(id='kpi-alta', className="mb-0 fw-bold", style={"color":"#443983"})
                ])]),),
                dbc.Col(dbc.Card([dbc.CardBody([
                    html.P("Media", className="small text-muted mb-1"),
                    html.H5(id='kpi-medio', className="mb-0 fw-bold", style={"color":"#31688e"})
                ])]),),
                dbc.Col(dbc.Card([dbc.CardBody([
                    html.P("Baja", className="small text-muted mb-1"),
                    html.H5(id='kpi-baja', className="mb-0 fw-bold", style={"color":"#35b779"})
                ])]),),
                dbc.Col(dbc.Card([dbc.CardBody([
                    html.P("Muy baja", className="small text-muted mb-1"),
                    html.H5(id='kpi-muybaja', className="mb-0 fw-bold", style={"color":"#856c04"})
                ])]),),
            ], className="g-2 my-2 row-cols-8"),

            dbc.Row([
                dbc.Col([
                    dcc.Graph(id='mapa-resumen', style={"height": "480px"})
                ], id='col-mapa-resumen', width=7),
                dbc.Col([
                    html.H6("Ranking municipios", className="fw-bold text-muted mb-2"),
                    dash_table.DataTable(
                        id='tabla-ranking',
                        columns=[
                            {"name": "Municipio",   "id": "name_en"},
                            {"name": "Prevalencia", "id": "ti_pred_mean_fmt"},
                            {"name": "Nivel",       "id": "categoria"},
                            {"name": "Región",      "id": "region"},
                        ],
                        style_table={"height": "460px", "overflowY": "auto"},
                        style_cell={"fontSize": "12px", "padding": "4px 8px",
                                    "textAlign": "left", "fontFamily": "sans-serif"},
                        style_header={"backgroundColor": VERDE, "color": "white",
                                      "fontWeight": "bold", "fontSize": "12px"},
                        style_data_conditional=[
                            {"if": {"filter_query": '{categoria} = "Muy alta"'},
                             "backgroundColor": "#440154", "color": "white"},
                            {"if": {"filter_query": '{categoria} = "Alta"'},
                             "backgroundColor": "#443983", "color": "white"},
                            {"if": {"filter_query": '{categoria} = "Media"'},
                             "backgroundColor": "#31688e", "color": "white"},
                            {"if": {"filter_query": '{categoria} = "Baja"'},
                             "backgroundColor": "#35b779", "color": "white"},
                            {"if": {"filter_query": '{categoria} = "Muy baja"'},
                             "backgroundColor": "#fde725", "color": "#333"},
                        ],
                        page_size=20,
                        sort_action="native",
                    )
                ], id='col-ranking-resumen', width=5),
            ], className="g-2"),
        ], fluid=True, className="px-3 py-2")
    ]),

    # ── Tab 2: Por región ─────────────────────────────────────────────────────
    dbc.Tab(label="Por región", tab_id="tab-region", children=[
        dbc.Container([
            dbc.Row([
                dbc.Col([
                    dcc.Graph(id='mapa-region', style={"height": "480px"})
                ], id='col-mapa-region', width=7),
                dbc.Col([
                    # Panel KPIs regional
                    html.H6("Indicadores regionales", className="fw-bold text-muted mb-2"),
                    dbc.Row([
                        dbc.Col(dbc.Card([dbc.CardBody([
                            html.P("Prevalencia", className="small text-muted mb-1"),
                            html.H5(id='reg-prev', className="mb-0 text-primary fw-bold")
                        ])]), width=12, className="mb-2"),
                    ]),
                    dbc.Row([
                        dbc.Col(dbc.Card([dbc.CardBody([
                            html.P("Niños", className="small text-muted mb-1"),
                            html.H5(id='reg-ninos', className="mb-0 fw-bold",
                                    style={"color":"#378ADD"})
                        ])]), width=6),
                        dbc.Col(dbc.Card([dbc.CardBody([
                            html.P("Niñas", className="small text-muted mb-1"),
                            html.H5(id='reg-ninas', className="mb-0 fw-bold",
                                    style={"color":"#D4537E"})
                        ])]), width=6),
                    ], className="mb-2"),
                    html.Hr(),
                    html.P("Municipios por nivel regional",
                           className="small fw-bold text-muted mb-2"),
                    dbc.Row([
                        dbc.Col(dbc.Card([dbc.CardBody([
                            html.P("Alto", className="small text-muted mb-1"),
                            html.H5(id='reg-alto', className="mb-0 fw-bold",
                                    style={"color":"#440154"})
                        ])]), width=4),
                        dbc.Col(dbc.Card([dbc.CardBody([
                            html.P("Medio", className="small text-muted mb-1"),
                            html.H5(id='reg-medio', className="mb-0 fw-bold",
                                    style={"color":"#31688e"})
                        ])]), width=4),
                        dbc.Col(dbc.Card([dbc.CardBody([
                            html.P("Bajo", className="small text-muted mb-1"),
                            html.H5(id='reg-bajo', className="mb-0 fw-bold",
                                    style={"color":"#fde725"})
                        ])]), width=4),
                    ], className="mb-2"),
                ], id='col-kpis-region', width=5),
            ], className="g-2 my-2"),
        ], fluid=True, className="px-3 py-2")
    ]),

    # ── Tab 3: Género ─────────────────────────────────────────────────────────
    dbc.Tab(label="Género", tab_id="tab-genero", children=[
        dbc.Container([
            dbc.Row([
                dbc.Col([
                    dcc.Graph(id='grafica-boxplot', style={"height": "300px"})
                ], width=6),
                dbc.Col([
                    dcc.Graph(id='grafica-brecha', style={"height": "300px"})
                ], width=6),
            ], className="g-2 my-2"),
            dbc.Row([
                dbc.Col([
                    dcc.Graph(id='grafica-boxplot-nivel', style={"height": "320px"})
                ], width=12),
            ], className="g-2"),
        ], fluid=True, className="px-3 py-2")
    ]),

    # ── Tab 4: Municipal ──────────────────────────────────────────────────────
    dbc.Tab(label="Municipal", tab_id="tab-municipal", children=[
        dbc.Container([
            dbc.Row([
                dbc.Col([
                    html.Label("Seleccionar municipio",
                               className="small fw-bold text-muted mb-1"),
                    dcc.Dropdown(id='dd-municipio',
                                 options=opciones_municipio,
                                 value=opciones_municipio[0]['value'],
                                 clearable=False)
                ], width=4, className="mb-3"),
            ]),
            # Ficha municipio
            dbc.Row([
                # Columna izquierda — datos básicos
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(id='mun-header',
                                       style={"background": VERDE, "color": "white",
                                              "fontWeight": "bold", "fontSize": "14px"}),
                        dbc.CardBody([
                            dbc.Row([
                                dbc.Col([
                                    html.P("Región", className="small text-muted mb-0"),
                                    html.H6(id='mun-region', className="fw-bold"),
                                ], width=6),
                                dbc.Col([
                                    html.P("Prevalencia TI", className="small text-muted mb-0"),
                                    html.H4(id='mun-prev', className="text-primary fw-bold"),
                                ], width=6),
                            ], className="mb-2"),
                            html.Hr(className="my-2"),
                            dbc.Row([
                                dbc.Col([
                                    html.P("Nivel nacional", className="small text-muted mb-0"),
                                    html.H5(id='mun-cat-nac'),
                                ], width=6),
                                dbc.Col([
                                    html.P("Nivel regional", className="small text-muted mb-0"),
                                    html.H5(id='mun-cat-reg'),
                                ], width=6),
                            ], className="mb-2"),
                            html.Hr(className="my-2"),
                            dbc.Row([
                                dbc.Col([
                                    html.P("Intervalo de confianza",
                                           className="small text-muted mb-0"),
                                    html.H6(id='mun-ic', className="fw-bold"),
                                ], width=12),
                            ], className="mb-2"),
                            html.Hr(className="my-2"),
                            dbc.Row([
                                dbc.Col([
                                    html.P("Total niños/as", className="small text-muted mb-0"),
                                    html.H5(id='mun-n', className="fw-bold"),
                                ], width=4),
                                dbc.Col([
                                    html.P("Prevalencia niños",
                                           className="small text-muted mb-0"),
                                    html.H5(id='mun-prev-ninos', className="fw-bold",
                                            style={"color":"#378ADD"}),
                                ], width=4),
                                dbc.Col([
                                    html.P("Prevalencia niñas",
                                           className="small text-muted mb-0"),
                                    html.H5(id='mun-prev-ninas', className="fw-bold",
                                            style={"color":"#D4537E"}),
                                ], width=4),
                            ]),
                        ])
                    ], className="h-100")
                ], width=4),

                # Columna derecha — gráfica comparativa
                dbc.Col([
                    dcc.Graph(id='mun-grafica', style={"height": "380px"})
                ], width=8),
            ], className="g-2"),
        ], fluid=True, className="px-3 py-2")
    ]),

    # ── Tab 5: Contexto ───────────────────────────────────────────────────────
    dbc.Tab(label="Contexto socioeconómico", tab_id="tab-contexto", children=[
        dbc.Container([
            dbc.Row([
                dbc.Col([dbc.Card([
                    dbc.CardHeader("Población 5-17 años",
                                   style={"background": "#185FA5", "color": "white",
                                          "fontSize": "13px", "fontWeight": "bold"}),
                    dbc.CardBody([
                        html.P("Total", className="text-muted mb-0 small"),
                        html.H4(id='s-total', className="text-primary mb-2"),
                        dbc.Row([
                            dbc.Col([html.P("Niños", className="small text-muted mb-0"),
                                     html.H6(id='s-ninos', style={"color":"#378ADD"}),
                                     html.P(id='s-ninos-p', className="small text-muted")]),
                            dbc.Col([html.P("Niñas", className="small text-muted mb-0"),
                                     html.H6(id='s-ninas', style={"color":"#D4537E"}),
                                     html.P(id='s-ninas-p', className="small text-muted")]),
                        ]),
                        html.Hr(className="my-2"),
                        html.P("Zona de residencia", className="small fw-bold text-muted mb-1"),
                        dbc.Row([
                            dbc.Col([html.P("Urbano", className="small text-muted mb-0"),
                                     html.H6(id='s-urb'),
                                     html.P(id='s-urb-p', className="small text-muted")]),
                            dbc.Col([html.P("Rural", className="small text-muted mb-0"),
                                     html.H6(id='s-rur'),
                                     html.P(id='s-rur-p', className="small text-muted")]),
                        ]),
                    ])
                ], className="h-100")], width=4),

                dbc.Col([dbc.Card([
                    dbc.CardHeader("Hogar y vivienda",
                                   style={"background": "#0F6E56", "color": "white",
                                          "fontSize": "13px", "fontWeight": "bold"}),
                    dbc.CardBody([
                        html.P("Jefatura del hogar",
                               className="small fw-bold text-muted mb-1"),
                        dbc.Row([
                            dbc.Col([html.P("Jefa mujer", className="small text-muted mb-0"),
                                     html.H6(id='s-jefa'),
                                     html.P(id='s-jefa-p', className="small text-muted")]),
                            dbc.Col([html.P("Jefe hombre", className="small text-muted mb-0"),
                                     html.H6(id='s-jefe'),
                                     html.P(id='s-jefe-p', className="small text-muted")]),
                        ]),
                        html.Hr(className="my-2"),
                        html.P("Acceso agua tubería",
                               className="small fw-bold text-muted mb-1"),
                        dbc.Row([
                            dbc.Col([html.P("Con acceso", className="small text-muted mb-0"),
                                     html.H6(id='s-agua-si'),
                                     html.P(id='s-agua-si-p', className="small text-muted")]),
                            dbc.Col([html.P("Sin acceso", className="small text-muted mb-0"),
                                     html.H6(id='s-agua-no'),
                                     html.P(id='s-agua-no-p', className="small text-muted")]),
                        ]),
                        html.Hr(className="my-2"),
                        html.P("Hacinamiento", className="small fw-bold text-muted mb-1"),
                        dbc.Row([
                            dbc.Col([html.P("Sin hacinamiento",
                                            className="small text-muted mb-0"),
                                     html.H6(id='s-hac-no'),
                                     html.P(id='s-hac-no-p', className="small text-muted")]),
                            dbc.Col([html.P("Con hacinamiento",
                                            className="small text-muted mb-0"),
                                     html.H6(id='s-hac-si'),
                                     html.P(id='s-hac-si-p', className="small text-muted")]),
                        ]),
                    ])
                ], className="h-100")], width=4),

                dbc.Col([dbc.Card([
                    dbc.CardHeader("Educación y territorio",
                                   style={"background": "#854F0B", "color": "white",
                                          "fontSize": "13px", "fontWeight": "bold"}),
                    dbc.CardBody([
                        html.P("Educación jefe/a hogar",
                               className="small fw-bold text-muted mb-1"),
                        dbc.Row([
                            dbc.Col([html.P("Primaria o menos",
                                            className="small text-muted mb-0"),
                                     html.H6(id='s-edu-pri'),
                                     html.P(id='s-edu-pri-p', className="small text-muted")]),
                            dbc.Col([html.P("Secundaria", className="small text-muted mb-0"),
                                     html.H6(id='s-edu-sec'),
                                     html.P(id='s-edu-sec-p', className="small text-muted")]),
                        ]),
                        dbc.Row([
                            dbc.Col([html.P("Terciaria", className="small text-muted mb-0"),
                                     html.H6(id='s-edu-ter'),
                                     html.P(id='s-edu-ter-p', className="small text-muted")]),
                        ]),
                        html.Hr(className="my-2"),
                        html.P("Tierra agrícola", className="small fw-bold text-muted mb-1"),
                        dbc.Row([
                            dbc.Col([html.P("Con tierra", className="small text-muted mb-0"),
                                     html.H6(id='s-tie-si'),
                                     html.P(id='s-tie-si-p', className="small text-muted")]),
                            dbc.Col([html.P("Sin tierra", className="small text-muted mb-0"),
                                     html.H6(id='s-tie-no'),
                                     html.P(id='s-tie-no-p', className="small text-muted")]),
                        ]),
                        html.Hr(className="my-2"),
                        html.P("Tasa neta matrícula secundaria",
                               className="small fw-bold text-muted mb-1"),
                        html.H4(id='s-tnc', className="text-warning"),
                    ])
                ], className="h-100")], width=4),
            ], className="g-2 my-2"),
        ], fluid=True, className="px-3 py-2")
    ]),

], id="tabs", active_tab="tab-resumen",
   className="mt-0",
   style={"borderTop": f"3px solid {VERDE}"},
   persistence=True)

app.layout = html.Div([
    HEADER,
    FILTROS,
    TABS,
    html.Footer(
        html.P("Fuente: Estimaciones SAE — Modelo GLMM | MIRTI 2026",
               className="text-muted text-center small py-2 mb-0"),
        className="border-top mt-2"
    )
])

# ==============================================================================
# 6. CALLBACKS
# ==============================================================================

@app.callback(
    Output('kpi-prev',    'children'),
    Output('kpi-ninos',   'children'),
    Output('kpi-ninas',   'children'),
    Output('kpi-muyalta', 'children'),
    Output('kpi-alta',    'children'),
    Output('kpi-medio',   'children'),
    Output('kpi-baja',    'children'),
    Output('kpi-muybaja', 'children'),
    Input('dd-region',    'value'),
)
def cb_kpis(region):
    df = filtrar(region)
    conteo = df['categoria'].value_counts()
    return (
        f"{df['ti_pred_mean'].mean():.1%}",
        f"{df['prev_hombre'].mean():.1%}",
        f"{df['prev_mujer'].mean():.1%}",
        f"{conteo.get('Muy alta', 0)} mun.",
        f"{conteo.get('Alta', 0)} mun.",
        f"{conteo.get('Media', 0)} mun.",
        f"{conteo.get('Baja', 0)} mun.",
        f"{conteo.get('Muy baja', 0)} mun.",
    )


@app.callback(
    Output('mapa-resumen',       'figure'),
    Output('tabla-ranking',      'data'),
    Output('col-mapa-resumen',   'width'),
    Output('col-ranking-resumen','style'),
    Input('dd-region',           'value'),
    Input('rd-mapa',             'value'),
)
def cb_resumen(region, tipo):
    df = filtrar(region)
    fig = make_mapa(df, tipo, 'total', regional=False)
    df_ord = df.sort_values('ti_pred_mean', ascending=False).copy()
    df_ord['ti_pred_mean_fmt'] = df_ord['ti_pred_mean'].apply(lambda x: f"{x:.1%}")
    if tipo == 'burbujas':
        return fig, df_ord[['name_en','ti_pred_mean_fmt','categoria','region']].to_dict('records'), 12, {"display": "none"}
    return fig, df_ord[['name_en','ti_pred_mean_fmt','categoria','region']].to_dict('records'), 7, {"display": "block"}


@app.callback(
    Output('mapa-region',     'figure'),
    Output('col-mapa-region', 'width'),
    Output('col-kpis-region', 'style'),
    Output('reg-prev',        'children'),
    Output('reg-ninos',       'children'),
    Output('reg-ninas',       'children'),
    Output('reg-alto',        'children'),
    Output('reg-medio',       'children'),
    Output('reg-bajo',        'children'),
    Input('dd-region',        'value'),
    Input('rd-mapa',          'value'),
)
def cb_region(region, tipo):
    df  = filtrar(region)
    fig_mapa = make_mapa(df, tipo, 'total', regional=True)
    conteo = df['categoria_regional'].value_counts()

    if tipo == 'burbujas':
        return (fig_mapa, 12, {"display": "none"},
                f"{df['ti_pred_mean'].mean():.1%}",
                f"{df['prev_hombre'].mean():.1%}",
                f"{df['prev_mujer'].mean():.1%}",
                f"{conteo.get('Alto', 0)} mun.",
                f"{conteo.get('Medio', 0)} mun.",
                f"{conteo.get('Bajo', 0)} mun.")

    return (fig_mapa, 7, {"display": "block"},
            f"{df['ti_pred_mean'].mean():.1%}",
            f"{df['prev_hombre'].mean():.1%}",
            f"{df['prev_mujer'].mean():.1%}",
            f"{conteo.get('Alto', 0)} mun.",
            f"{conteo.get('Medio', 0)} mun.",
            f"{conteo.get('Bajo', 0)} mun.")


@app.callback(
    Output('grafica-boxplot',       'figure'),
    Output('grafica-brecha',        'figure'),
    Output('grafica-boxplot-nivel', 'figure'),
    Input('dd-region',              'value'),
)
def cb_genero(region):
    df = filtrar(region)
    df = df.copy()
    df['brecha'] = df['prev_hombre'] - df['prev_mujer']

    # Boxplot distribución general
    df_melt = df[['name_en','prev_hombre','prev_mujer']].melt(
        id_vars='name_en', var_name='sexo', value_name='prevalencia')
    df_melt['sexo'] = df_melt['sexo'].map({'prev_hombre':'Niños','prev_mujer':'Niñas'})
    fig_box = px.box(df_melt, x='sexo', y='prevalencia', color='sexo',
                     color_discrete_map={'Niños':'#378ADD','Niñas':'#D4537E'},
                     title='Distribución por género',
                     labels={'prevalencia':'Prevalencia TI','sexo':''})
    fig_box.update_layout(showlegend=False, yaxis_tickformat='.1%', margin={"t":40})

    # Brecha
    df_top = df.nlargest(15, 'brecha')
    fig_brecha = px.bar(df_top, x='name_en', y='brecha',
                        color='brecha', color_continuous_scale='RdBu_r',
                        title='Top 15 — Brecha género (niños − niñas)',
                        labels={'brecha':'Brecha','name_en':''})
    fig_brecha.update_layout(yaxis_tickformat='.1%', xaxis_tickangle=-40,
                              margin={"t":40,"b":80})

    # Boxplot por nivel de riesgo
    df_nivel = df[['name_en','categoria','prev_hombre','prev_mujer']].melt(
        id_vars=['name_en','categoria'], var_name='sexo', value_name='prevalencia')
    df_nivel['sexo'] = df_nivel['sexo'].map({'prev_hombre':'Niños','prev_mujer':'Niñas'})
    df_nivel['categoria'] = pd.Categorical(df_nivel['categoria'],
                                            categories=ORDEN_CAT, ordered=True)
    df_nivel = df_nivel.sort_values('categoria')

    fig_nivel = px.box(df_nivel, x='categoria', y='prevalencia',
                       color='sexo',
                       color_discrete_map={'Niños':'#378ADD','Niñas':'#D4537E'},
                       title='Distribución de prevalencia por nivel de riesgo y género',
                       labels={'prevalencia':'Prevalencia TI',
                               'categoria':'Nivel de riesgo', 'sexo':''},
                       category_orders={'categoria': ORDEN_CAT})
    fig_nivel.update_layout(yaxis_tickformat='.1%', margin={"t":40},
                             legend_title="")
    return fig_box, fig_brecha, fig_nivel


@app.callback(
    Output('mun-header',     'children'),
    Output('mun-region',     'children'),
    Output('mun-prev',       'children'),
    Output('mun-cat-nac',    'children'),
    Output('mun-cat-reg',    'children'),
    Output('mun-ic',         'children'),
    Output('mun-n',          'children'),
    Output('mun-prev-ninos', 'children'),
    Output('mun-prev-ninas', 'children'),
    Output('mun-grafica',    'figure'),
    Input('dd-municipio',    'value'),
)
def cb_municipal(ubigeo):
    row = df_completo[df_completo['ubigeo'] == ubigeo].iloc[0]
    region_num = int(row['region'])
    nombre_reg = nombres_reg.get(region_num, f"Región {region_num}")

    # Gráfica comparativa — municipio vs región
    df_reg = df_completo[df_completo['region'] == region_num].copy()
    df_reg = df_reg.sort_values('ti_pred_mean', ascending=True)
    colores_bar = ['#440154' if u == ubigeo else '#31688e'
                   for u in df_reg['ubigeo']]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df_reg['ti_pred_mean'],
        y=df_reg['name_en'],
        orientation='h',
        marker_color=colores_bar,
        text=df_reg['ti_pred_mean'].apply(lambda x: f"{x:.1%}"),
        textposition='outside',
        name='Prevalencia'
    ))
    fig.update_layout(
        title=f"Municipios de {nombre_reg} — municipio seleccionado en morado",
        xaxis_tickformat='.1%',
        margin={"t":50,"b":20,"l":150,"r":60},
        height=max(300, len(df_reg) * 22),
        showlegend=False
    )

    # Color del nivel nacional
    colores_nivel = {
        'Muy alta': '#440154', 'Alta': '#443983',
        'Media': '#31688e', 'Baja': '#35b779', 'Muy baja': '#856c04'
    }
    colores_nivel_reg = {'Alto': '#440154', 'Medio': '#31688e', 'Bajo': '#fde725'}

    cat_nac = str(row['categoria'])
    cat_reg = str(row['categoria_regional'])

    return (
        str(row['name_en']),
        nombre_reg,
        f"{row['ti_pred_mean']:.1%}",
        html.Span(cat_nac, style={"color": colores_nivel.get(cat_nac, '#333'),
                                   "fontWeight": "bold"}),
        html.Span(cat_reg, style={"color": colores_nivel_reg.get(cat_reg, '#333'),
                                   "fontWeight": "bold"}),
        f"{row['ti_pred_lower']:.1%} — {row['ti_pred_upper']:.1%}",
        f"{int(row['n']):,}",
        f"{row['prev_hombre']:.1%}",
        f"{row['prev_mujer']:.1%}",
        fig
    )


@app.callback(
    Output('s-total',    'children'), Output('s-ninos',    'children'),
    Output('s-ninos-p',  'children'), Output('s-ninas',    'children'),
    Output('s-ninas-p',  'children'), Output('s-urb',      'children'),
    Output('s-urb-p',    'children'), Output('s-rur',      'children'),
    Output('s-rur-p',    'children'), Output('s-jefa',     'children'),
    Output('s-jefa-p',   'children'), Output('s-jefe',     'children'),
    Output('s-jefe-p',   'children'), Output('s-agua-si',  'children'),
    Output('s-agua-si-p','children'), Output('s-agua-no',  'children'),
    Output('s-agua-no-p','children'), Output('s-hac-no',   'children'),
    Output('s-hac-no-p', 'children'), Output('s-hac-si',   'children'),
    Output('s-hac-si-p', 'children'), Output('s-edu-pri',  'children'),
    Output('s-edu-pri-p','children'), Output('s-edu-sec',  'children'),
    Output('s-edu-sec-p','children'), Output('s-edu-ter',  'children'),
    Output('s-edu-ter-p','children'), Output('s-tie-si',   'children'),
    Output('s-tie-si-p', 'children'), Output('s-tie-no',   'children'),
    Output('s-tie-no-p', 'children'), Output('s-tnc',      'children'),
    Input('dd-region', 'value'),
)
def cb_socio(region):
    f = df_socio[df_socio['codigo'] == region].iloc[0]
    n = lambda c: f"{int(f[c]):,}"
    p = lambda c: f"{f[c]:.1%}"
    return (
        n('n_total'),
        n('n_ninos'),        p('pct_ninos'),
        n('n_ninas'),        p('pct_ninas'),
        n('zona_urbano_n'),  p('zona_urbano_pct'),
        n('zona_rural_n'),   p('zona_rural_pct'),
        n('hogar_jefa_mujer_n'),  p('hogar_jefa_mujer_pct'),
        n('hogar_jefe_hombre_n'), p('hogar_jefe_hombre_pct'),
        n('agua_agua_tubería_n'),     p('agua_agua_tubería_pct'),
        n('agua_sin_agua_tubería_n'), p('agua_sin_agua_tubería_pct'),
        n('hacin_sin_hacinamiento_n'), p('hacin_sin_hacinamiento_pct'),
        n('hacin_hacinamiento_n'),     p('hacin_hacinamiento_pct'),
        n('edu_primaria_o_menos_n'),  p('edu_primaria_o_menos_pct'),
        n('edu_secundaria_n'),        p('edu_secundaria_pct'),
        n('edu_terciaria_n'),         p('edu_terciaria_pct'),
        n('tierra_con_tierra_agricultura_n'), p('tierra_con_tierra_agricultura_pct'),
        n('tierra_sin_tierra_agricultura_n'), p('tierra_sin_tierra_agricultura_pct'),
        f"{f['tnc_sec_mean']:.1%}"
    )

# ==============================================================================
# 7. RUN
# ==============================================================================
if __name__ == '__main__':
    app.run(debug=False)
