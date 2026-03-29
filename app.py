# ==============================================================================
# app.py — Dashboard Trabajo Infantil República Dominicana
# ==============================================================================

import dash
from dash import dcc, html, Input, Output, callback
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
data_dir = Path(r"C:\Users\jcgb7\OneDrive\MIRTI_2026\Republica_Dominicana\Censo\proyecto_rd_censo\dashboard\data")

# Cargar GeoJSON municipal
with open(data_dir / "municipios_rd.geojson", encoding="utf-8") as f:
    geojson_municipios = json.load(f)

# Cargar GeoJSON regional
with open(data_dir / "regiones_rd.geojson", encoding="utf-8") as f:
    geojson_regiones = json.load(f)

# Cargar datos tabulares
est_municipal = pd.read_csv(data_dir / "est_municipal.csv")
est_municipal['ubigeo'] = est_municipal['ubigeo'].astype(str).str.zfill(4)

genero_df = pd.read_csv(data_dir / "genero_municipal.csv")
genero_df['ubigeo'] = genero_df['ubigeo'].astype(str).str.zfill(4)

# Cargar GeoDataFrame para centroides
gdf = gpd.read_file(data_dir / "municipios_rd.geojson")
gdf['ubigeo'] = gdf['ubigeo'].astype(str).str.zfill(4)

# Unir genero con estimaciones
est_municipal['categoria'] = est_municipal['categoria'].astype(str)

# Agregar nombre de municipio
nombres_mun = gdf[['ubigeo', 'name_en']].copy()
df_completo = est_municipal.merge(genero_df, on=['ubigeo', 'region'], how='left')
df_completo = df_completo.merge(nombres_mun, on='ubigeo', how='left')

# Agregar nombres de regiones
gdf_reg = gpd.read_file(data_dir / "regiones_rd.geojson")
gdf_reg['region'] = gdf_reg['cod_reg'].astype(int)
nombres_reg = dict(zip(gdf_reg['region'], gdf_reg['name_es']))

# Regiones disponibles
regiones = sorted(est_municipal['region'].unique())

df_socio = pd.read_csv(data_dir / "resumen_socioeconomico.csv")

print(f"✓ Resumen socioeconómico: {len(df_socio)} filas")
print("✓ Datos cargados correctamente")
print(f"  Municipios: {len(est_municipal)}")
print(f"  Regiones: {len(regiones)}")

# ==============================================================================
# 2. INICIALIZAR APP
# ==============================================================================
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.FLATLY],
    title="Trabajo Infantil — República Dominicana"
)

# ==============================================================================
# 3. COLORES Y CATEGORÍAS
# ==============================================================================
# Colores Viridis 5 niveles
colores_categoria = {
    'Muy baja': '#fde725',  # viridis(4) — amarillo
    'Baja':     '#35b779',  # viridis(3) — verde
    'Media':    '#31688e',  # viridis(2) — azul medio
    'Alta':     '#443983',  # viridis(1) — azul oscuro
    'Muy alta': '#440154',  # viridis(0) — morado
    'Sin datos':'#cccccc'
}

# Límites reales de categorías
min_prev = est_municipal['ti_pred_mean'].min()
max_prev = est_municipal['ti_pred_mean'].max()
amplitud = (max_prev - min_prev) / 5
limites = [min_prev + i * amplitud for i in range(6)]

etiquetas_categoria = {
    'Muy baja': f"Muy baja ({limites[0]*100:.1f}% - {limites[1]*100:.1f}%)",
    'Baja':     f"Baja ({limites[1]*100:.1f}% - {limites[2]*100:.1f}%)",
    'Media':    f"Media ({limites[2]*100:.1f}% - {limites[3]*100:.1f}%)",
    'Alta':     f"Alta ({limites[3]*100:.1f}% - {limites[4]*100:.1f}%)",
    'Muy alta': f"Muy alta ({limites[4]*100:.1f}% - {limites[5]*100:.1f}%)",
}

# ==============================================================================
# 4. LAYOUT
# ==============================================================================
app.layout = dbc.Container([

# ── Encabezado ────────────────────────────────────────────────────────────
    dbc.Row([
        dbc.Col([
            html.H2("Modelo de Identificación del Riesgo de Trabajo Infantil (MIRTI) en República Dominicana",
                    className="text-white mb-0"),
            html.P("Estimaciones de Áreas Pequeñas (SAE) — Modelo GLMM",
                   className="mb-0",
                   style={"color": "rgba(255,255,255,0.7)"})
        ])
    ], className="p-3 mb-4 rounded", style={"background": "#00542A"}),

    # ── Filtros ───────────────────────────────────────────────────────────────
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Label("Filtrar por región:", className="fw-bold"),
                    dcc.Dropdown(
                        id='filtro-region',
                        options=[{'label': 'Todas las regiones', 'value': 0}] +
                                [{'label': f"Región {r} — {nombres_reg.get(r, '')}", 'value': r} for r in regiones],
                        value=0,
                        clearable=False
                    )
                ])
            ])
        ], width=4),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Label("Tipo de mapa:", className="fw-bold"),
                    dcc.RadioItems(
                        id='tipo-mapa',
                        options=[
                            {'label': '  Coroplético', 'value': 'coropletico'},
                            {'label': '  Burbujas',    'value': 'burbujas'},
                        ],
                        value='coropletico',
                        inline=True,
                        inputStyle={"margin-right": "6px", "margin-left": "12px"}
                    )
                ])
            ])
        ], width=4),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Label("Variable:", className="fw-bold"),
                    dcc.RadioItems(
                        id='tipo-variable',
                        options=[
                            {'label': '  Prevalencia total', 'value': 'total'},
                            {'label': '  Niños',             'value': 'hombre'},
                            {'label': '  Niñas',             'value': 'mujer'},
                        ],
                        value='total',
                        inline=True,
                        inputStyle={"margin-right": "6px", "margin-left": "12px"}
                    )
                ])
            ])
        ], width=4),
    ], className="mb-4"),

    # ── Fila 1 KPIs: prevalencias ─────────────────────────────────────────────
    dbc.Row([
        dbc.Col(dbc.Card([
            dbc.CardBody([
                html.H6("Prevalencia nacional", className="text-muted"),
                html.H3(id='kpi-nacional', className="text-primary")
            ])
        ]), width=3),
        dbc.Col(dbc.Card([
            dbc.CardBody([
                html.H6("Prevalencia niños", className="text-muted"),
                html.H3(id='kpi-ninos', className="text-info")
            ])
        ]), width=3),
        dbc.Col(dbc.Card([
            dbc.CardBody([
                html.H6("Prevalencia niñas", className="text-muted"),
                html.H3(id='kpi-ninas', className="text-success")
            ])
        ]), width=3),
        dbc.Col(dbc.Card([
            dbc.CardBody([
                html.H6("Total municipios", className="text-muted"),
                html.H3(id='kpi-total', className="text-secondary")
            ])
        ]), width=3),
    ], className="mb-2"),

    # ── Fila 2 KPIs: conteo por categoría ────────────────────────────────────
    dbc.Row([
        dbc.Col(dbc.Card([
            dbc.CardBody([
                html.H6("Muy baja", className="text-muted small"),
                html.H4(id='kpi-muybaja', style={"color": "#fde725"})
            ])
        ]), width=2),
        dbc.Col(dbc.Card([
            dbc.CardBody([
                html.H6("Baja", className="text-muted small"),
                html.H4(id='kpi-baja', style={"color": "#35b779"})
            ])
        ]), width=2),
        dbc.Col(dbc.Card([
            dbc.CardBody([
                html.H6("Media", className="text-muted small"),
                html.H4(id='kpi-media', style={"color": "#31688e"})
            ])
        ]), width=2),
        dbc.Col(dbc.Card([
            dbc.CardBody([
                html.H6("Alta", className="text-muted small"),
                html.H4(id='kpi-alta', style={"color": "#443983"})
            ])
        ]), width=2),
        dbc.Col(dbc.Card([
            dbc.CardBody([
                html.H6("Muy alta", className="text-muted small"),
                html.H4(id='kpi-muyalta', style={"color": "#440154"})
            ])
        ]), width=2),
        dbc.Col(dbc.Card([
            dbc.CardBody([
                html.H6("Sin categoría", className="text-muted small"),
                html.H4(id='kpi-sincategoria', className="text-muted")
            ])
        ]), width=2),
    ], className="mb-4"),

    # ── Mapa + Gráfica género ─────────────────────────────────────────────────
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    dcc.Graph(id='mapa-principal', style={"height": "550px"})
                ])
            ])
        ], width=7),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    dcc.Graph(id='grafica-genero', style={"height": "550px"})
                ])
            ])
        ], width=5),
    ], className="mb-4"),

    # ── Top 10 barras ─────────────────────────────────────────────────────────
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    dcc.Graph(id='grafica-municipios', style={"height": "380px"})
                ])
            ])
        ], width=12),
    ], className="mb-4"),

    # ── Panel socioeconómico — 3 tarjetas ─────────────────────────────────────
    dbc.Row([

        # Tarjeta 1 — Población
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([
                    html.Span("Población 5-17 años",
                              className="fw-bold text-white",
                              style={"fontSize": "14px"})
                ], style={"background": "#185FA5"}),
                dbc.CardBody([
                    # Total
                    html.Div([
                        html.Div([
                            html.P("Total niños/as", className="text-muted mb-0",
                                   style={"fontSize": "11px"}),
                            html.H4(id='socio-total', className="mb-0 text-primary")
                        ], className="mb-3"),
                    ]),
                    html.Hr(className="my-2"),
                    # Niños vs niñas
                    html.Div([
                        html.Div([
                            html.P("Niños", className="text-muted mb-0",
                                   style={"fontSize": "11px"}),
                            html.H5(id='socio-ninos', style={"color": "#378ADD"}),
                            html.P(id='socio-ninos-pct', className="text-muted",
                                   style={"fontSize": "11px"})
                        ], style={"display": "inline-block", "width": "48%"}),
                        html.Div([
                            html.P("Niñas", className="text-muted mb-0",
                                   style={"fontSize": "11px"}),
                            html.H5(id='socio-ninas', style={"color": "#D4537E"}),
                            html.P(id='socio-ninas-pct', className="text-muted",
                                   style={"fontSize": "11px"})
                        ], style={"display": "inline-block", "width": "48%"}),
                    ]),
                    html.Hr(className="my-2"),
                    # Zona
                    html.P("Zona de residencia", className="text-muted mb-1 fw-bold",
                           style={"fontSize": "11px"}),
                    html.Div([
                        html.Div([
                            html.P("Urbano", className="text-muted mb-0",
                                   style={"fontSize": "11px"}),
                            html.H6(id='socio-urbano', className="mb-0"),
                            html.P(id='socio-urbano-pct', className="text-muted",
                                   style={"fontSize": "10px"})
                        ], style={"display": "inline-block", "width": "48%"}),
                        html.Div([
                            html.P("Rural", className="text-muted mb-0",
                                   style={"fontSize": "11px"}),
                            html.H6(id='socio-rural', className="mb-0"),
                            html.P(id='socio-rural-pct', className="text-muted",
                                   style={"fontSize": "10px"})
                        ], style={"display": "inline-block", "width": "48%"}),
                    ]),
                ])
            ], className="h-100")
        ], width=4),

        # Tarjeta 2 — Hogar y vivienda
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([
                    html.Span("Hogar y vivienda",
                              className="fw-bold text-white",
                              style={"fontSize": "14px"})
                ], style={"background": "#0F6E56"}),
                dbc.CardBody([
                    # Jefe hogar
                    html.P("Jefatura del hogar", className="text-muted mb-1 fw-bold",
                           style={"fontSize": "11px"}),
                    html.Div([
                        html.Div([
                            html.P("Jefa mujer", className="text-muted mb-0",
                                   style={"fontSize": "11px"}),
                            html.H6(id='socio-jefa-n', className="mb-0"),
                            html.P(id='socio-jefa-pct', className="text-muted",
                                   style={"fontSize": "10px"})
                        ], style={"display": "inline-block", "width": "48%"}),
                        html.Div([
                            html.P("Jefe hombre", className="text-muted mb-0",
                                   style={"fontSize": "11px"}),
                            html.H6(id='socio-jefe-n', className="mb-0"),
                            html.P(id='socio-jefe-pct', className="text-muted",
                                   style={"fontSize": "10px"})
                        ], style={"display": "inline-block", "width": "48%"}),
                    ]),
                    html.Hr(className="my-2"),
                    # Agua
                    html.P("Acceso agua tubería", className="text-muted mb-1 fw-bold",
                           style={"fontSize": "11px"}),
                    html.Div([
                        html.Div([
                            html.P("Con acceso", className="text-muted mb-0",
                                   style={"fontSize": "11px"}),
                            html.H6(id='socio-agua-si-n', className="mb-0"),
                            html.P(id='socio-agua-si-pct', className="text-muted",
                                   style={"fontSize": "10px"})
                        ], style={"display": "inline-block", "width": "48%"}),
                        html.Div([
                            html.P("Sin acceso", className="text-muted mb-0",
                                   style={"fontSize": "11px"}),
                            html.H6(id='socio-agua-no-n', className="mb-0"),
                            html.P(id='socio-agua-no-pct', className="text-muted",
                                   style={"fontSize": "10px"})
                        ], style={"display": "inline-block", "width": "48%"}),
                    ]),
                    html.Hr(className="my-2"),
                    # Hacinamiento
                    html.P("Hacinamiento", className="text-muted mb-1 fw-bold",
                           style={"fontSize": "11px"}),
                    html.Div([
                        html.Div([
                            html.P("Sin hacinamiento", className="text-muted mb-0",
                                   style={"fontSize": "11px"}),
                            html.H6(id='socio-hacin-no-n', className="mb-0"),
                            html.P(id='socio-hacin-no-pct', className="text-muted",
                                   style={"fontSize": "10px"})
                        ], style={"display": "inline-block", "width": "48%"}),
                        html.Div([
                            html.P("Con hacinamiento", className="text-muted mb-0",
                                   style={"fontSize": "11px"}),
                            html.H6(id='socio-hacin-si-n', className="mb-0"),
                            html.P(id='socio-hacin-si-pct', className="text-muted",
                                   style={"fontSize": "10px"})
                        ], style={"display": "inline-block", "width": "48%"}),
                    ]),
                ])
            ], className="h-100")
        ], width=4),

        # Tarjeta 3 — Educación y territorio
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([
                    html.Span("Educación y territorio",
                              className="fw-bold text-white",
                              style={"fontSize": "14px"})
                ], style={"background": "#854F0B"}),
                dbc.CardBody([
                    # Educación jefe hogar
                    html.P("Educación jefe/a hogar", className="text-muted mb-1 fw-bold",
                           style={"fontSize": "11px"}),
                    html.Div([
                        html.Div([
                            html.P("Primaria o menos", className="text-muted mb-0",
                                   style={"fontSize": "11px"}),
                            html.H6(id='socio-edu-pri-n', className="mb-0"),
                            html.P(id='socio-edu-pri-pct', className="text-muted",
                                   style={"fontSize": "10px"})
                        ], style={"display": "inline-block", "width": "48%"}),
                        html.Div([
                            html.P("Secundaria", className="text-muted mb-0",
                                   style={"fontSize": "11px"}),
                            html.H6(id='socio-edu-sec-n', className="mb-0"),
                            html.P(id='socio-edu-sec-pct', className="text-muted",
                                   style={"fontSize": "10px"})
                        ], style={"display": "inline-block", "width": "48%"}),
                    ]),
                    html.Div([
                        html.Div([
                            html.P("Terciaria", className="text-muted mb-0",
                                   style={"fontSize": "11px"}),
                            html.H6(id='socio-edu-ter-n', className="mb-0"),
                            html.P(id='socio-edu-ter-pct', className="text-muted",
                                   style={"fontSize": "10px"})
                        ], style={"display": "inline-block", "width": "48%"}),
                    ]),
                    html.Hr(className="my-2"),
                    # Tierra agrícola
                    html.P("Tierra agrícola", className="text-muted mb-1 fw-bold",
                           style={"fontSize": "11px"}),
                    html.Div([
                        html.Div([
                            html.P("Con tierra", className="text-muted mb-0",
                                   style={"fontSize": "11px"}),
                            html.H6(id='socio-tierra-si-n', className="mb-0"),
                            html.P(id='socio-tierra-si-pct', className="text-muted",
                                   style={"fontSize": "10px"})
                        ], style={"display": "inline-block", "width": "48%"}),
                        html.Div([
                            html.P("Sin tierra", className="text-muted mb-0",
                                   style={"fontSize": "11px"}),
                            html.H6(id='socio-tierra-no-n', className="mb-0"),
                            html.P(id='socio-tierra-no-pct', className="text-muted",
                                   style={"fontSize": "10px"})
                        ], style={"display": "inline-block", "width": "48%"}),
                    ]),
                    html.Hr(className="my-2"),
                    # Matrícula secundaria
                    html.P("Tasa neta matrícula secundaria",
                           className="text-muted mb-1 fw-bold",
                           style={"fontSize": "11px"}),
                    html.H4(id='socio-tnc', className="text-warning"),
                ])
            ], className="h-100")
        ], width=4),

    ], className="mb-4"),

    # ── Pie categorías ────────────────────────────────────────────────────────
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    dcc.Graph(id='grafica-categorias', style={"height": "350px"})
                ])
            ])
        ], width=6),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    dcc.Graph(id='grafica-brecha', style={"height": "350px"})
                ])
            ])
        ], width=6),
    ], className="mb-4"),

    # ── Pie de página ─────────────────────────────────────────────────────────
    dbc.Row([
        dbc.Col([
            html.P("Fuente: Estimaciones de Áreas Pequeñas (SAE) — Modelo GLMM | MIRTI 2026",
                   className="text-muted text-center small")
        ])
    ])

], fluid=True)

# ==============================================================================
# 5. CALLBACKS
# ==============================================================================

def filtrar_datos(region):
    """Filtra los datos según la región seleccionada."""
    if region == 0:
        return df_completo, gdf
    else:
        df_f = df_completo[df_completo['region'] == region].copy()
        gdf_f = gdf[gdf['region'] == region].copy()
        return df_f, gdf_f


@app.callback(
    Output('kpi-nacional',      'children'),
    Output('kpi-ninos',         'children'),
    Output('kpi-ninas',         'children'),
    Output('kpi-total',         'children'),
    Output('kpi-muybaja',       'children'),
    Output('kpi-baja',          'children'),
    Output('kpi-media',         'children'),
    Output('kpi-alta',          'children'),
    Output('kpi-muyalta',       'children'),
    Output('kpi-sincategoria',  'children'),
    Input('filtro-region',      'value'),
)
def actualizar_kpis(region):
    df_f, _ = filtrar_datos(region)

    prevalencia = df_f['ti_pred_mean'].mean()
    prev_ninos  = df_f['prev_hombre'].mean()
    prev_ninas  = df_f['prev_mujer'].mean()
    total       = len(df_f)

    conteo = df_f['categoria'].value_counts()
    muy_baja     = conteo.get('Muy baja', 0)
    baja         = conteo.get('Baja', 0)
    media        = conteo.get('Media', 0)
    alta         = conteo.get('Alta', 0)
    muy_alta     = conteo.get('Muy alta', 0)
    sin_cat      = conteo.get('nan', 0) + conteo.get('None', 0)

    return (
        f"{prevalencia:.1%}",
        f"{prev_ninos:.1%}",
        f"{prev_ninas:.1%}",
        f"{total} municipios",
        f"{muy_baja} municipios",
        f"{baja} municipios",
        f"{media} municipios",
        f"{alta} municipios",
        f"{muy_alta} municipios",
        f"{sin_cat} municipios"
    )


@app.callback(
    Output('mapa-principal', 'figure'),
    Input('filtro-region',   'value'),
    Input('tipo-mapa',       'value'),
    Input('tipo-variable',   'value'),
)
def actualizar_mapa(region, tipo_mapa, tipo_variable):
    df_f, gdf_f = filtrar_datos(region)

    # Seleccionar variable a mapear
    if tipo_variable == 'total':
        col_valor = 'ti_pred_mean'
        titulo_var = 'Prevalencia TI'
    elif tipo_variable == 'hombre':
        col_valor = 'prev_hombre'
        titulo_var = 'Prevalencia TI — Niños'
    else:
        col_valor = 'prev_mujer'
        titulo_var = 'Prevalencia TI — Niñas'

    centro_lat = gdf_f.geometry.centroid.y.mean()
    centro_lon = gdf_f.geometry.centroid.x.mean()

    if tipo_mapa == 'coropletico':
        fig = px.choropleth_mapbox(
            df_f,
            geojson=geojson_municipios,
            locations='ubigeo',
            featureidkey='properties.ubigeo',
            color='categoria',
            color_discrete_map=colores_categoria,
            category_orders={'categoria': ['Muy baja', 'Baja', 'Media', 'Alta', 'Muy alta']},
            mapbox_style='carto-positron',
            zoom=6.5,
            center={"lat": centro_lat, "lon": centro_lon},
            opacity=0.8,
            hover_name='name_en',
            hover_data={
                col_valor: ':.1%',
                'categoria': True,
                'n': True,
                'ubigeo': True
            },
            labels={
                col_valor: titulo_var,
                'categoria': 'Nivel de riesgo',
                'n': 'Total niños/as',
                'ubigeo': 'Código',
                'name_en': 'Municipio'
            },
            title=f"Nivel de riesgo de trabajo infantil por municipio"
        )
    else:
        # Mapa de burbujas
        gdf_f['centroid_x'] = gdf_f.geometry.centroid.x
        gdf_f['centroid_y'] = gdf_f.geometry.centroid.y
        df_burbuja = df_f.merge(
            gdf_f[['ubigeo', 'centroid_x', 'centroid_y']], on='ubigeo', how='left'
        )
        fig = px.scatter_mapbox(
            df_burbuja,
            lat='centroid_y',
            lon='centroid_x',
            size='n',
            color=col_valor,
            color_continuous_scale='Viridis',
            mapbox_style='carto-positron',
            zoom=6.5,
            center={"lat": centro_lat, "lon": centro_lon},
            hover_name='ubigeo',
            hover_data={col_valor: ':.1%', 'n': True},
            labels={col_valor: titulo_var, 'n': 'Total niños/as'},
            title=f"{titulo_var} — Tamaño = total niños/as"
        )

    fig.update_layout(margin={"r": 0, "t": 40, "l": 0, "b": 0})
    return fig


@app.callback(
    Output('grafica-genero',  'figure'),
    Input('filtro-region',    'value'),
)
def actualizar_genero(region):
    df_f, _ = filtrar_datos(region)

    df_gen = df_f[['ubigeo', 'prev_hombre', 'prev_mujer']].melt(
        id_vars='ubigeo',
        value_vars=['prev_hombre', 'prev_mujer'],
        var_name='sexo',
        value_name='prevalencia'
    )
    df_gen['sexo'] = df_gen['sexo'].map({
        'prev_hombre': 'Niños', 'prev_mujer': 'Niñas'
    })

    fig = px.box(
        df_gen,
        x='sexo',
        y='prevalencia',
        color='sexo',
        color_discrete_map={'Niños': '#378ADD', 'Niñas': '#D4537E'},
        title='Distribución de prevalencia por género',
        labels={'prevalencia': 'Prevalencia TI', 'sexo': ''}
    )
    fig.update_layout(
        showlegend=False,
        yaxis_tickformat='.1%',
        margin={"t": 40}
    )
    return fig


@app.callback(
    Output('grafica-municipios', 'figure'),
    Input('filtro-region',       'value'),
    Input('tipo-variable',       'value'),
)
def actualizar_barras(region, tipo_variable):
    df_f, _ = filtrar_datos(region)

    col_valor = {
        'total':  'ti_pred_mean',
        'hombre': 'prev_hombre',
        'mujer':  'prev_mujer'
    }[tipo_variable]

    # Top 20 ordenado de mayor a menor
    df_ord = df_f.nlargest(20, col_valor).sort_values(col_valor, ascending=False)

    fig = px.bar(
        df_ord,
        x='name_en',
        y=col_valor,
        color='categoria',
        color_discrete_map=colores_categoria,
        category_orders={
            'categoria': ['Muy baja', 'Baja', 'Media', 'Alta', 'Muy alta'],
            'name_en': df_ord['name_en'].tolist()  # respeta el orden por prevalencia
        },
        title='Top 20 municipios por prevalencia de trabajo infantil',
        labels={
            col_valor: 'Prevalencia TI',
            'name_en': 'Municipio',
            'categoria': 'Nivel de riesgo'
        },
        hover_data={
            col_valor: ':.1%',
            'categoria': True,
            'n': True,
            'ubigeo': True
        }
    )
    fig.update_layout(
        yaxis_tickformat='.1%',
        xaxis_tickangle=-45,
        margin={"t": 40},
        legend_title="Nivel de riesgo"
    )
    return fig


@app.callback(
    Output('grafica-categorias', 'figure'),
    Input('filtro-region',       'value'),
)
def actualizar_categorias(region):
    df_f, _ = filtrar_datos(region)

    orden = ['Muy baja', 'Baja', 'Media', 'Alta', 'Muy alta']
    conteo = df_f['categoria'].value_counts().reindex(orden).reset_index()
    conteo.columns = ['categoria', 'municipios']

    fig = px.pie(
        conteo,
        names='categoria',
        values='municipios',
        color='categoria',
        color_discrete_map=colores_categoria,
        title='Distribución por categoría de riesgo',
        category_orders={'categoria': orden}
    )
    fig.update_layout(margin={"t": 40})
    return fig


@app.callback(
    Output('grafica-brecha', 'figure'),
    Input('filtro-region',   'value'),
)
def actualizar_brecha(region):
    df_f, _ = filtrar_datos(region)

    df_f = df_f.copy()
    df_f['brecha'] = df_f['prev_hombre'] - df_f['prev_mujer']
    df_ord = df_f.nlargest(15, 'brecha')

    fig = px.bar(
        df_ord,
        x='ubigeo',
        y='brecha',
        color='brecha',
        color_continuous_scale='RdBu_r',
        title='Top 15 municipios — Brecha de género (niños − niñas)',
        labels={'brecha': 'Brecha', 'ubigeo': 'Municipio'}
    )
    fig.update_layout(
        yaxis_tickformat='.1%',
        xaxis_tickangle=-45,
        margin={"t": 40}
    )
    return fig

    
@app.callback(
    Output('socio-total',        'children'),
    Output('socio-ninos',        'children'),
    Output('socio-ninos-pct',    'children'),
    Output('socio-ninas',        'children'),
    Output('socio-ninas-pct',    'children'),
    Output('socio-urbano',       'children'),
    Output('socio-urbano-pct',   'children'),
    Output('socio-rural',        'children'),
    Output('socio-rural-pct',    'children'),
    Output('socio-jefa-n',       'children'),
    Output('socio-jefa-pct',     'children'),
    Output('socio-jefe-n',       'children'),
    Output('socio-jefe-pct',     'children'),
    Output('socio-agua-si-n',    'children'),
    Output('socio-agua-si-pct',  'children'),
    Output('socio-agua-no-n',    'children'),
    Output('socio-agua-no-pct',  'children'),
    Output('socio-hacin-no-n',   'children'),
    Output('socio-hacin-no-pct', 'children'),
    Output('socio-hacin-si-n',   'children'),
    Output('socio-hacin-si-pct', 'children'),
    Output('socio-edu-pri-n',    'children'),
    Output('socio-edu-pri-pct',  'children'),
    Output('socio-edu-sec-n',    'children'),
    Output('socio-edu-sec-pct',  'children'),
    Output('socio-edu-ter-n',    'children'),
    Output('socio-edu-ter-pct',  'children'),
    Output('socio-tierra-si-n',  'children'),
    Output('socio-tierra-si-pct','children'),
    Output('socio-tierra-no-n',  'children'),
    Output('socio-tierra-no-pct','children'),
    Output('socio-tnc',          'children'),
    Input('filtro-region',       'value'),
)
def actualizar_socio(region):
    fila = df_socio[df_socio['codigo'] == region].iloc[0]

    def fmt_n(col):   return f"{int(fila[col]):,}"
    def fmt_pct(col): return f"{fila[col]:.1%}"

    return (
        fmt_n('n_total'),
        fmt_n('n_ninos'),        fmt_pct('pct_ninos'),
        fmt_n('n_ninas'),        fmt_pct('pct_ninas'),
        fmt_n('zona_urbano_n'),  fmt_pct('zona_urbano_pct'),
        fmt_n('zona_rural_n'),   fmt_pct('zona_rural_pct'),
        fmt_n('hogar_jefa_mujer_n'),  fmt_pct('hogar_jefa_mujer_pct'),
        fmt_n('hogar_jefe_hombre_n'), fmt_pct('hogar_jefe_hombre_pct'),
        fmt_n('agua_agua_tubería_n'),     fmt_pct('agua_agua_tubería_pct'),
        fmt_n('agua_sin_agua_tubería_n'), fmt_pct('agua_sin_agua_tubería_pct'),
        fmt_n('hacin_sin_hacinamiento_n'), fmt_pct('hacin_sin_hacinamiento_pct'),
        fmt_n('hacin_hacinamiento_n'),     fmt_pct('hacin_hacinamiento_pct'),
        fmt_n('edu_primaria_o_menos_n'),  fmt_pct('edu_primaria_o_menos_pct'),
        fmt_n('edu_secundaria_n'),        fmt_pct('edu_secundaria_pct'),
        fmt_n('edu_terciaria_n'),         fmt_pct('edu_terciaria_pct'),
        fmt_n('tierra_con_tierra_agricultura_n'), fmt_pct('tierra_con_tierra_agricultura_pct'),
        fmt_n('tierra_sin_tierra_agricultura_n'), fmt_pct('tierra_sin_tierra_agricultura_pct'),
        f"{fila['tnc_sec_mean']:.1%}"
    )

# ==============================================================================
# 6. CORRER APP
# ==============================================================================
server = app  # necesario para Render
if __name__ == '__main__':
    app.run(debug=False)