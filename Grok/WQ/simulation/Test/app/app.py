#!/usr/bin/env python3
"""Dash app to browse WaveQLab3D station time series."""

import argparse
import glob
import hashlib
import os
import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple, NamedTuple

try:
    from typing import TypedDict
except ImportError:
    try:
        from typing_extensions import TypedDict
    except ImportError:
        TypedDict = dict

import hashlib
import plotly.graph_objects as go
from plotly.colors import qualitative as plotly_qual
from dash import ALL, Dash, Input, Output, State, dcc, html
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc

# --- 1. SETUP & HELPER CLASSES ---

class TimeSeries(TypedDict):
    t: List[float]
    vx: List[float]
    vy: List[float]
    vz: List[float]

# Try to import ctx
try:
    from dash import ctx
except ImportError:
    ctx = None

# Regex patterns
FNAME_RE = re.compile(
    r"^(?P<dataset>.+?)_(?P<q>[^_]+)_(?P<r>[^_]+)_(?P<s>[^_]+)_(?P<block>block[^.]+)\.dat$",
    flags=re.IGNORECASE,
)
STATION_NAME_RE = re.compile(
    r"^(?P<dataset>.+?)_station_(?P<station>[A-Za-z0-9]+)\.dat$",
    flags=re.IGNORECASE,
)
NUM_RE = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eEdD][+-]?\d+)?"
XYZ_RE = re.compile(
    rf"^(?P<dataset>.+?)_(?P<x>{NUM_RE})_(?P<y>{NUM_RE})_(?P<z>{NUM_RE})\.dat$",
    flags=re.IGNORECASE,
)

class DatasetInfo(NamedTuple):
    path: Path
    dataset: str
    station: str

VARIANT_ELASTIC = "elastic"
VARIANT_ANELASTIC = "anelastic"

PML_TOKEN_RE = re.compile(r"^pml-(?P<mode>[^_]+)$", flags=re.IGNORECASE)
RES_TOKEN_RE = re.compile(r"^res-(?P<value>[^_]+)$", flags=re.IGNORECASE)
TEST_TOKEN_RE = re.compile(r"(?:^|[_-])test[-_]?(?P<id>\d+[a-z0-9]*)", flags=re.IGNORECASE)
CG_VALUE_RE = re.compile(rf"(?:^|[_-])cg-(?P<val>{NUM_RE})(?:[_-]|$)", flags=re.IGNORECASE)
ANELASTIC_GAMMA_RE = re.compile(r"anelastic[-_]gamma-(?P<val>[+-]?(?:\d+(?:\.\d+)?|\.\d+))", flags=re.IGNORECASE)
ANELASTIC_RE = re.compile(r"(?:^|[_-])anelastic(?:[_-]|$)", flags=re.IGNORECASE)
ELASTIC_RE = re.compile(r"(?:^|[_-])elastic(?:[_-]|$)", flags=re.IGNORECASE)
STENCIL_SET = {"traditional", "upwind", "upwind-drp"}

# --- 2. HELPER FUNCTIONS ---

def dataset_base_and_variant(dataset_name: str) -> Tuple[str, Optional[str]]:
    name = dataset_name
    if name.endswith('.dat'):
        name = name[:-4]

    # If filename ends with three numeric components (x_y_z) treat those as station coords
    parts = name.split('_')
    if len(parts) > 3 and all(re.match(r'^-?\d+(\.\d+)?$', p) for p in parts[-3:]):
        name = '_'.join(parts[:-3])

    # Try to pull out explicit variant tokens (anelastic/elastic) so callers get a clean base
    # Prefer the more specific anelastic-gamma token, falling back to plain 'elastic'
    m = ANELASTIC_GAMMA_RE.search(name)
    if m:
        # remove the matched token from the base name but keep separators
        base = ANELASTIC_GAMMA_RE.sub('_', name)
        base = re.sub(r'_+', '_', base).strip('_')
        return base, m.group('val')
    if ANELASTIC_RE.search(name):
        base = ANELASTIC_RE.sub('_', name)
        base = re.sub(r'_+', '_', base).strip('_')
        return base, 'anelastic'
    if ELASTIC_RE.search(name):
        base = ELASTIC_RE.sub('_', name)
        base = re.sub(r'_+', '_', base).strip('_')
        return base, 'elastic'

    return name, None


def parse_stencil_order_pml_ver(base: str) -> Optional[Tuple[str, str, str, str, str]]:
    parts = [p for p in base.split('_') if p]
    if len(parts) < 2:
        return None

    stencil = ""
    order = ""
    idx = -1
    for i, p in enumerate(parts[:-1]):
        if p.lower() in STENCIL_SET:
            stencil = p
            order = parts[i + 1]
            idx = i + 2
            break
    if not stencil or not order or idx < 0:
        return None

    res_value = ""
    pml_mode: Optional[str] = None
    rest: List[str] = []

    for p in parts[idx:]:
        if pml_mode is None:
            mres = RES_TOKEN_RE.match(p)
            if mres and not res_value:
                res_value = mres.group('value')
                continue
            m = PML_TOKEN_RE.match(p)
            if m:
                pml_mode = m.group('mode').lower()
                continue
        else:
            rest.append(p)

    if not pml_mode:
        return None

    if not rest:
        ver = ""
    elif rest[0].lower() == 'b' and len(rest) >= 2:
        ver = '_'.join(rest[1:])
    else:
        ver = '_'.join(rest)

    return stencil, order, res_value, pml_mode, ver

def parse_test_id(dataset: str) -> str:
    m = TEST_TOKEN_RE.search(dataset)
    return m.group('id') if m else ""

def parse_cg_value(dataset: str) -> str:
    m = CG_VALUE_RE.search(dataset)
    return m.group('val') if m else ""

def parse_variant_gamma(dataset: str) -> Tuple[Optional[str], Optional[str]]:
    m = ANELASTIC_GAMMA_RE.search(dataset)
    if m:
        return VARIANT_ANELASTIC, m.group('val')
    if ANELASTIC_RE.search(dataset):
        return VARIANT_ANELASTIC, ""
    if ELASTIC_RE.search(dataset):
        return VARIANT_ELASTIC, "0.0"
    return None, None

def pml_label(pml_mode: str) -> str:
    mode = (pml_mode or "").lower()
    if mode == "off":
        return "0.0"
    if mode == "on":
        return "3.0"
    if mode == "60":
        return "6.0"
    # Try to extract leading numeric value (strip units like 'km' or 'm')
    m = re.match(r"([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)", mode)
    if m:
        return m.group(1)
    return pml_mode

def iter_dataset_files(data_dirs: Iterable[Path]) -> List[Path]:
    patterns = ["*.dat"]
    files: List[Path] = []
    for data_root in data_dirs:
        for pat in patterns:
            files.extend(Path(p).resolve() for p in glob.glob(str(Path(data_root) / pat)))
    seen_paths: Set[Path] = set()
    unique_files: List[Path] = []
    for path in files:
        if path.is_file() and path not in seen_paths:
            seen_paths.add(path)
            unique_files.append(path)
    unique_files.sort(key=lambda p: p.name)
    return unique_files

def parse_dataset_info(path: Path) -> Optional[DatasetInfo]:
    if path.suffix.lower() != ".dat":
        return None
    stem = path.stem
    parts = stem.split('_')
    if len(parts) >= 3 and all(re.match(r'^-?\d+(\.\d+)?$', p) for p in parts[-3:]):
        station = f"{parts[-3]}_{parts[-2]}_{parts[-1]}"
        dataset = '_'.join(parts[:-3])
        return DatasetInfo(path=path, dataset=dataset, station=station)

    m2 = STATION_NAME_RE.match(path.name)
    if m2:
        dataset = m2.group("dataset")
        station = f"station_{m2.group('station')}"
        return DatasetInfo(path=path, dataset=dataset, station=station)

    m3 = XYZ_RE.match(path.name)
    if m3:
        dataset = m3.group("dataset")
        x, y, z = m3.group("x"), m3.group("y"), m3.group("z")
        station = f"{x}_{y}_{z}"
        return DatasetInfo(path=path, dataset=dataset, station=station)

    if len(parts) >= 5:
        dataset = "_".join(parts[:-4])
        q, r, s, block = parts[-4], parts[-3], parts[-2], parts[-1]
        if dataset and block.lower().startswith("block"):
            station = f"{q}_{r}_{s}_{block}"
            return DatasetInfo(path=path, dataset=dataset, station=station)
    return None

def load_timeseries(path: Path) -> TimeSeries:
    t, vx, vy, vz = [], [], [], []
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for raw in f:
            line = raw.strip()
            if not line: continue
            parts = line.split()
            if len(parts) < 4: continue
            try:
                tt, vxx, vyy, vzz = (float(parts[0]), float(parts[1]), float(parts[2]), float(parts[3]))
            except ValueError: continue
            t.append(tt); vx.append(vxx); vy.append(vyy); vz.append(vzz)
    return {"t": t, "vx": vx, "vy": vy, "vz": vz}

PALETTE = list(plotly_qual.Plotly) or ["#1f77b4"]

def dataset_color(ds_name: str) -> str:
    digest = hashlib.sha256(ds_name.encode("utf-8")).digest()
    idx = int.from_bytes(digest[:4], "big") % len(PALETTE)
    return PALETTE[idx]


def make_figure(station: str, selected: List[DatasetInfo], plot: str, properties: Dict[str, Dict[str, float]], height: int = 400, show_title: bool = False) -> go.Figure:
    plot_meta = {
        "vx": (f"Radial velocity at station {station}", "vx"),
        "vy": (f"Transverse velocity at station {station}", "vy"),
        "vz": (f"Vertical velocity at station {station}", "vz"),
    }
    if plot not in plot_meta:
        fig = go.Figure()
        fig.add_annotation(text="Invalid plot", showarrow=False)
        return fig

    # Use descriptive y-axis labels (RTZ) and plot velocities in cm/s
    y_label_map = {
        "vx": "Radial Velocity (cm/s)",
        "vy": "Transverse Velocity (cm/s)",
        "vz": "Vertical Velocity (cm/s)",
    }

    title, y_col = plot_meta[plot]
    fig = go.Figure()
    for info in selected:
        df = load_timeseries(info.path)
        # Use test id (e.g. '1x', '1y', '1z') as the legend label
        test_id = parse_test_id(info.dataset)
        label = test_id if test_id else info.dataset
        props = properties.get(label, {})
        color = props.get('color') or dataset_color(info.dataset)
        width = props.get('width', 3)  # Thicker default line
        dash = props.get('dash', 'solid')
        # Convert velocities from m/s to cm/s for plotting
        y_vals_cm = [v * 100.0 for v in df[y_col]]
        fig.add_trace(go.Scatter(
            x=df["t"], y=y_vals_cm, mode="lines", name=label,
            line=dict(color=color, width=width, dash=dash),
            showlegend=True
        ))

    y_axis_title = y_label_map.get(plot, "particle velocity (cm/s)")
    layout_dict = dict(
        height=height,
        margin=dict(l=60, r=30, t=60, b=60),
        xaxis_title="Time (s)",
        yaxis_title=y_axis_title,
        font=dict(family="Arial, sans-serif", size=20),
        plot_bgcolor="white",
        paper_bgcolor="white",
        legend=dict(
            font=dict(size=18),
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            borderwidth=0,
            bgcolor="rgba(0,0,0,0)",
            itemwidth=60
        ),
    )
    if show_title:
        layout_dict["title"] = dict(
            text=title,
            font=dict(size=22, family="Arial, sans-serif", color="#222"),
            x=0.5,
            xanchor="center"
        )
    fig.update_layout(**layout_dict)
    fig.update_xaxes(
        showline=True, linewidth=2, linecolor="black",
        mirror=True, ticks="outside", tickwidth=2, tickcolor="black", ticklen=8,
        gridcolor="#e5e5e5", gridwidth=1,
        zeroline=False,
        title_font=dict(size=22, family="Arial, sans-serif", color="#222"),
        tickfont=dict(size=18, family="Arial, sans-serif", color="#222")
    )
    fig.update_yaxes(
        showline=True, linewidth=2, linecolor="black",
        mirror=True, ticks="outside", tickwidth=2, tickcolor="black", ticklen=8,
        gridcolor="#e5e5e5", gridwidth=1,
        zeroline=False,
        title_font=dict(size=22, family="Arial, sans-serif", color="#222"),
        tickfont=dict(size=18, family="Arial, sans-serif", color="#222")
    )
    return fig

def build_index(data_dirs: Iterable[Path]) -> Tuple[List[DatasetInfo], List[str]]:
    infos: List[DatasetInfo] = []
    for path in iter_dataset_files(data_dirs):
        info = parse_dataset_info(path)
        if info is not None:
            infos.append(info)
    stations = sorted({i.station for i in infos})
    return infos, stations

def group_by_station(infos: Iterable[DatasetInfo]) -> Dict[str, List[DatasetInfo]]:
    out: Dict[str, List[DatasetInfo]] = {}
    for i in infos:
        out.setdefault(i.station, []).append(i)
    for st in out:
        out[st].sort(key=lambda x: x.dataset)
    return out

# --- 3. GLOBAL INITIALIZATION (Executed on Import) ---

# Argument Parsing (handled safely for Gunicorn)
# We use argparse primarily to find the Data Dir, but fallback to environment/CWD
parser = argparse.ArgumentParser()
parser.add_argument("--data-dir", default=None, help="Directory containing station .dat files")
parser.add_argument("--host", default="0.0.0.0")
parser.add_argument("--port", type=int, default=8050)
parser.add_argument("--debug", action="store_true")

# In Gunicorn/Production, sys.argv might not be what we expect, so we catch errors
# or rely on defaults.
try:
    args, unknown = parser.parse_known_args()
except SystemExit:
    # If argparse fails (e.g. during build), just use defaults
    args = argparse.Namespace(data_dir=None, host="0.0.0.0", port=8050, debug=False)

# Locate Data Directory
script_dir = Path(__file__).resolve().parent
candidates = [
    Path.cwd() / "data_rtz",
    Path.cwd() / "data",
    Path.cwd() / "waveqlab3d/simulation/plots",
    script_dir / "waveqlab3d/simulation/plots",
    script_dir / "data",
    script_dir,
]
# If --data-dir was passed, prioritize it
if args.data_dir:
    candidates.insert(0, Path(args.data_dir).expanduser().resolve())

data_dir = next((p.resolve() for p in candidates if p.exists()), candidates[-1].resolve())

data_dirs: List[Path] = []
data_dirs.append(data_dir)
for extra_base in (Path.cwd(), script_dir):
    filtered = extra_base / "data_rtz_filtered"
    if filtered.exists():
        filtered_resolved = filtered.resolve()
        if filtered_resolved not in data_dirs:
            data_dirs.append(filtered_resolved)

# Initialize Data Index
all_infos, stations = build_index(data_dirs)
by_station = group_by_station(all_infos)

# Initialize App
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# CRITICAL: Expose server for Gunicorn
server = app.server

# Setup Defaults for Layout
preferred_station = "12.000_0.000_9.000"
if preferred_station in stations:
    initial_station = preferred_station
elif stations:
    initial_station = stations[0]
else:
    initial_station = ""
initial_infos = by_station.get(initial_station, [])
initial_selected_infos = [initial_infos[0]] if initial_infos else []
initial_plots = ["vx", "vy", "vz"]
initial_figs = [make_figure(initial_station, initial_selected_infos, p, {}, 400) for p in initial_plots]

# --- 4. LAYOUT DEFINITION ---

app.layout = dbc.Container(
    [
        dbc.Row([
            dbc.Col(
                html.Div(
                    html.H2("Station viewer: Withers (P)", style={"margin": "0", "padding": "12px 0", "textAlign": "center", "fontWeight": "bold"}),
                    style={
                        "background": "#f8f9fa",
                        "borderBottom": "2px solid #dee2e6",
                        "width": "100%",
                        "position": "fixed",
                        "top": 0,
                        "left": 0,
                        "zIndex": 1000,
                        "height": "60px"
                    }
                ),
                width=12
            )
        ], style={"marginBottom": "72px"}),
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.Label("Select Depth (y)"),
                        dcc.Dropdown(
                            id="depth-dropdown",
                            options=[{"label": str(y), "value": str(y)} for y in sorted({s.split('_')[1] for s in stations})],
                            value=(stations[0].split('_')[1] if stations else ""),
                            multi=False, clearable=False, placeholder="Choose depth",
                        ),
                        html.Div(id="xz-table-container", style={"marginTop": "8px"}),
                        # keep station-dropdown as the internal selected station value
                        dcc.Store(id="station-dropdown", data=initial_station),
                        html.Hr(),
                        html.Label("Datasets"),
                        html.Button("Clear Dataset Selections", id="clear-dataset-button", style={"marginLeft": "10px"}),
                        # Column selector always visible
                        html.Div([
                            html.Label("Show columns:"),
                            dcc.Checklist(
                                id="dataset-table-column-selector",
                                options=[
                                    {"label": "Test", "value": "test"},
                                    {"label": "Stencil", "value": "stencil"},
                                    {"label": "Order", "value": "order"},
                                    {"label": "Res", "value": "res"},
                                    {"label": "PML", "value": "pml"},
                                    {"label": "Response", "value": "response"},
                                    {"label": "CG", "value": "cg"}
                                ],
                                value=["test", "stencil", "pml", "response"],
                                inline=True,
                                inputStyle={"marginRight": "4px"},
                                style={"marginLeft": "8px"}
                            )
                        ], style={"marginBottom": "8px"}),
                        dcc.Store(id="dataset-path-map", data={}),
                        dcc.Store(id="dataset-base-order", data=[]),
                        dcc.Store(id="dataset-selection-store", data={}),
                        html.Div(id="dataset-table-container"),
                        html.Hr(),
                        html.Hr(),
                        html.Label("Adjust line properties:"),
                        dcc.Store(id="line-properties-store", data={}),
                        html.Div(id="line-controls-container"),
                        html.Hr(),
                        html.Label("Adjust plot height:"),
                        dcc.Slider(id="plot-height-slider", min=200, max=800, value=400, step=50, marks={200:'200', 400:'400', 600:'600', 800:'800'}),
                        html.Div([
                            html.Label("Select timeseries plot(s):"),
                            html.Br(),
                            dcc.Checklist(
                                id="plot-checklist",
                                options=[
                                    {"label": "Radial", "value": "vx"},
                                    {"label": "Transverse", "value": "vy"},
                                    {"label": "Vertical", "value": "vz"}
                                ],
                                value=initial_plots,
                                labelStyle={"display": "inline-block", "marginRight": "20px", "whiteSpace": "nowrap"},
                                style={"display": "flex", "flexDirection": "row", "gap": "10px", "marginTop": "4px"},
                            ),
                            dcc.Checklist(
                                id="plot-title-toggle",
                                options=[{"label": "Plot Title", "value": "show_title"}],
                                value=[],
                                style={"marginTop": "8px", "marginLeft": "2px"},
                                inputStyle={"marginRight": "6px"}
                            )
                        ], style={"marginTop": "12px", "marginBottom": "8px"}),
                        html.Hr(),
                    ],
                    style={
                        "flex": "0 0 30%",
                        "maxWidth": "30%",
                        "overflowY": "auto",
                        "maxHeight": "95vh",
                    },
                ),
                dbc.Col(
                    [
                        html.Div(id="plot-container", children=[dcc.Graph(figure=fig) for fig in initial_figs])
                    ],
                    style={
                        "flex": "0 0 70%",
                        "maxWidth": "70%",
                        "overflowY": "auto",
                        "maxHeight": "95vh",
                    },
                ),
            ],
            align="start",
        ),
    ],
    fluid=True,
    className="p-3",
)

# --- 5. CALLBACKS ---

@app.callback(Output("xz-table-container", "children"), [Input("depth-dropdown", "value"), Input("station-dropdown", "data")])
def render_xz_table(depth_value: str, current_station: str):
    # Build a table of X,Z positions available at this depth (y)
    if not depth_value or depth_value is None:
        if stations:
            depth_value = stations[0].split('_')[1]
        else:
            return html.Div("No stations available")
    
    # find stations matching the selected depth
    matches = [s for s in stations if s.split('_')[1] == str(depth_value)]
    if not matches:
        return html.Div(f"No stations at depth {depth_value}")
    # gather unique sorted X and Z values
    xs = sorted({s.split('_')[0] for s in matches}, key=lambda v: float(v))
    zs = sorted({s.split('_')[2] for s in matches}, key=lambda v: float(v))
    stations_set = set(matches)

    # Render all X columns and let the container scroll horizontally
    xs_vis = xs
    header_cells = [html.Th("Z / X", style={"textAlign": "center"})]
    for x in xs_vis:
        try:
            x_float = float(x)
            if x_float.is_integer():
                x_val = f"{int(x_float)}"
            else:
                x_val = f"{x_float:.2f}"
        except Exception:
            x_val = x
        header_cells.append(html.Th(x_val, style={"textAlign": "center"}))
    header = html.Thead(html.Tr(header_cells))

    body_rows = []
    for z in zs:
        try:
            z_float = float(z)
            if z_float.is_integer():
                z_val = f"{int(z_float)}"
            else:
                z_val = f"{z_float:.2f}"
        except Exception:
            z_val = z
        row_cells = [html.Th(z_val, style={"textAlign": "center"})]
        for x in xs_vis:
            coord = f"{x}_{depth_value}_{z}"
            if coord in stations_set:
                # Clickable circle: filled (●) if selected, empty (○) if not
                is_selected = (coord == current_station)
                symbol = "●" if is_selected else "○"
                cell = html.Div(
                    symbol,
                    id={"type": "xz-cell", "coord": coord},
                    n_clicks=0,
                    style={
                        "cursor": "pointer",
                        "fontSize": "14px",
                        "fontWeight": "bold",
                        "userSelect": "none",
                        "textAlign": "center",
                        "margin": "0",
                        "padding": "0",
                        "lineHeight": "1.1",
                        "height": "18px",
                        "width": "18px",
                        "display": "inline-flex",
                        "alignItems": "center",
                        "justifyContent": "center"
                    },
                    title=f"Click to select {coord}"
                )
            else:
                cell = html.Div()
            # Remove horizontal padding for radio button cells, match style to first column
            row_cells.append(html.Td(cell, style={"textAlign": "center"}))
        body_rows.append(html.Tr(row_cells))
    
    table = dbc.Table(
        [header, html.Tbody(body_rows)],
        bordered=True,
        size="sm",
        style={
            "whiteSpace": "nowrap",
            "borderCollapse": "collapse",
            "margin": "0",
            "padding": "0"
        },
        className="table-compact"
    )

    # Wrap table in a horizontally scrollable container so the user can pan across X
    # Add compact cell padding via inline style for all cells
    return html.Div(
        table,
        style={
            "overflowX": "auto",
            "marginTop": "8px",
            "fontSize": "15px"
        }
    )


@app.callback(Output("station-dropdown", "data"), Input({"type": "xz-cell", "coord": ALL}, "n_clicks"), State({"type": "xz-cell", "coord": ALL}, "id"))
def select_station_from_xz(n_clicks_list, ids):
    # Determine which circle was just clicked
    # Determine which circle was just clicked. Dash sometimes gives a prop_id
    # string in JSON or Python-literal form; try several robust parsing methods
    # and fall back to inspecting the n_clicks_list/ids arrays.
    if not n_clicks_list:
        raise PreventUpdate

    # Try to read the triggered prop from the callback context first.
    coord = None
    try:
        triggered = ctx.triggered if ctx else []
    except Exception:
        triggered = []

    if triggered:
        pid = triggered[0].get("prop_id", "")
        if pid and ".n_clicks" in pid:
            prop_id_part = pid.split('.', 1)[0]
            # Try JSON first, then Python literal fallback (ast.literal_eval)
            try:
                import json
                id_dict = json.loads(prop_id_part)
            except Exception:
                try:
                    import ast
                    id_dict = ast.literal_eval(prop_id_part)
                except Exception:
                    id_dict = None
            if isinstance(id_dict, dict):
                coord = id_dict.get("coord")

    # If we couldn't get coord from ctx, fall back to inspecting n_clicks_list
    if not coord:
        # compute max clicks (treat None as 0)
        try:
            max_clicks = max([v or 0 for v in n_clicks_list])
        except ValueError:
            raise PreventUpdate
        if not max_clicks:
            raise PreventUpdate
        # prefer the last index that has the max value (most recently clicked)
        indices = [i for i, v in enumerate(n_clicks_list) if (v or 0) == max_clicks]
        if not indices:
            raise PreventUpdate
        idx = indices[-1]
        if isinstance(ids, (list, tuple)) and idx < len(ids):
            id_obj = ids[idx]
            if isinstance(id_obj, dict):
                coord = id_obj.get("coord")

    if coord:
        return coord

    raise PreventUpdate


@app.callback(
    [Output("dataset-table-container", "children"),
     Output("dataset-path-map", "data"),
     Output("dataset-base-order", "data")],
    [Input("station-dropdown", "data"),
     Input("dataset-selection-store", "data"),
     Input("dataset-table-column-selector", "value")]
)
def update_dataset_table(selected_station: str, selection_store: Dict, selected_columns=None):
    infos = by_station.get(selected_station or "", [])
    stencil_to_variants: Dict[str, Dict[Tuple[str, str, str, str, str], Dict[str, str]]] = {}
    base_to_cg: Dict[str, str] = {}
    base_to_gamma: Dict[str, str] = {}
    
    for info in infos:
        base, _ = dataset_base_and_variant(info.dataset)
        test_id = parse_test_id(info.dataset)
        variant, gamma = parse_variant_gamma(info.dataset)
        if variant not in (VARIANT_ELASTIC, VARIANT_ANELASTIC):
            continue
        parsed = parse_stencil_order_pml_ver(base)
        if parsed is None:
            continue
        stencil, order, res, pml_mode, ver = parsed
        key = (test_id, order, res, pml_mode, ver)
        if stencil not in stencil_to_variants: stencil_to_variants[stencil] = {}
        if key not in stencil_to_variants[stencil]: stencil_to_variants[stencil][key] = {}
        stencil_to_variants[stencil][key].setdefault(variant, str(info.path))
        base_key = f"test{test_id}_{stencil}_{order}" if test_id else f"{stencil}_{order}"
        if res:
            base_key += f"_res-{res}"
        base_key += f"_pml-{pml_mode}"
        if ver:
            base_key += f"_{ver}"
        if base_key not in base_to_cg:
            base_to_cg[base_key] = parse_cg_value(info.dataset)
        if variant == VARIANT_ANELASTIC and gamma and base_key not in base_to_gamma:
            base_to_gamma[base_key] = gamma

    sorted_stencils = sorted(stencil_to_variants.keys(), key=lambda s: ['traditional', 'upwind', 'upwind-drp'].index(s) if s in ['traditional', 'upwind', 'upwind-drp'] else 999)
    grouped = {}
    base_order = []

    def test_sort_key(base: str) -> Tuple[int, str]:
        # Extract test number from base string, default to large if not found
        m = re.search(r"test(\d+)([a-z0-9]*)", base)
        if m:
            return (int(m.group(1)), m.group(2) or "")
        return (10**9, "")

    # Collect all (base, key) pairs across all stencils
    all_base_keys = []
    for stencil in sorted_stencils:
        keys = list(stencil_to_variants[stencil].keys())
        for key in keys:
            test_id, order, res, pml_mode, ver = key
            base = f"test{test_id}_{stencil}_{order}" if test_id else f"{stencil}_{order}"
            if res:
                base += f"_res-{res}"
            base += f"_pml-{pml_mode}"
            if ver:
                base += f"_{ver}"
            all_base_keys.append((base, key, stencil))

    # Sort all_base_keys by test number, then by base name
    all_base_keys_sorted = sorted(all_base_keys, key=lambda x: (test_sort_key(x[0]), x[0]))

    for base, key, stencil in all_base_keys_sorted:
        grouped[base] = stencil_to_variants[stencil][key]
        base_order.append(base)

    has_any_selection = False
    for base in base_order:
        saved = selection_store.get(base, {}) if isinstance(selection_store, dict) else {}
        if bool(saved.get(VARIANT_ELASTIC)) or bool(saved.get(VARIANT_ANELASTIC)):
            has_any_selection = True; break

    if not has_any_selection and base_order:
        first_base = base_order[0]
        selection_store = dict(selection_store or {})
        selection_store.setdefault(first_base, {})
        if grouped[first_base].get(VARIANT_ELASTIC):
            selection_store[first_base][VARIANT_ELASTIC] = True
        elif grouped[first_base].get(VARIANT_ANELASTIC):
            selection_store[first_base][VARIANT_ANELASTIC] = True


    # Column selector
    all_columns = [
        ("Test", "test"),
        ("Stencil", "stencil"),
        ("Order", "order"),
        ("Res", "res"),
        ("PML", "pml"),
        ("Response", "response"),
        ("CG", "cg"),
    ]
    # Default: CG, Order, Res unselected
    default_selected = ["test", "stencil", "pml", "response"]
    if selected_columns is None:
        selected_columns = default_selected
    # column_selector is now in the main layout

    stencil_legend = html.Div([
        html.Span("Stencil: ", style={"fontWeight": "bold"}),
        html.Span("t = traditional, u = upwind, d = upwind-drp", style={"fontStyle": "italic"})
    ], style={"marginBottom": "6px"})

    # Only include selected columns in header
    col_map = {
        "test": html.Th("Test", id={"type": "col-header", "col": "test"}, style={"textAlign": "center", "verticalAlign": "middle"}),
        "stencil": html.Th("Stencil", id={"type": "col-header", "col": "stencil"}, style={"textAlign": "center", "verticalAlign": "middle"}),
        "order": html.Th("Order", id={"type": "col-header", "col": "order"}, style={"textAlign": "center", "verticalAlign": "middle"}),
        "res": html.Th("Res", id={"type": "col-header", "col": "res"}, style={"textAlign": "center", "verticalAlign": "middle"}),
        "pml": html.Th("PML", id={"type": "col-header", "col": "pml"}, style={"textAlign": "center", "verticalAlign": "middle"}),
        "response": html.Th("Response", id={"type": "col-header", "col": "response"}, style={"textAlign": "center", "verticalAlign": "middle"}),
        "cg": html.Th("CG", id={"type": "col-header", "col": "cg"}, style={"textAlign": "center", "verticalAlign": "middle"}),
    }
    header = html.Thead(html.Tr([col_map[c] for c in selected_columns]))


    # Build table rows directly from base_order. Merge Elastic and Anelastic into one 'Response' column.
    rows = []
    stencil_abbr = {"traditional": "t", "upwind": "u", "upwind-drp": "d"}
    for base in base_order:
        variants = grouped.get(base, {})
        elastic_path = variants.get(VARIANT_ELASTIC)
        anelastic_path = variants.get(VARIANT_ANELASTIC)
        saved = selection_store.get(base, {}) if isinstance(selection_store, dict) else {}

        # Elastic checklist: label 'E' for elastic
        elastic_check = dcc.Checklist(
            id={"type": "dataset-elastic", "base": base},
            options=[{"label": "E", "value": "on", "disabled": elastic_path is None}],
            value=["on"] if bool(saved.get(VARIANT_ELASTIC)) and elastic_path else [],
            style={"display": "inline-block", "marginRight": "8px"}
        )
        # Anelastic checklist: label 'A' for anelastic
        anelastic_check = dcc.Checklist(
            id={"type": "dataset-anelastic", "base": base},
            options=[{"label": "A", "value": "on", "disabled": anelastic_path is None}],
            value=["on"] if bool(saved.get(VARIANT_ANELASTIC)) and anelastic_path else [],
            style={"display": "inline-block"}
        )
        response_cell = html.Td([
            elastic_check,
            anelastic_check
        ], style={"textAlign": "center", "whiteSpace": "nowrap"})

        # Try to extract display tokens from base string for nicer columns
        test_val = parse_test_id(base)
        cg_val = base_to_cg.get(base, "")

        m_pml = re.search(r"pml-(?P<mode>[^_]+)", base, flags=re.IGNORECASE)
        pml_val = pml_label(m_pml.group('mode')) if m_pml else "-"
        m_res = re.search(r"res-(?P<value>[^_]+)", base, flags=re.IGNORECASE)
        res_display = m_res.group('value') if m_res else "-"
        m_stencil = re.search(r"(traditional|upwind|upwind-drp)_([^_]+)", base)
        if m_stencil:
            stencil_full = m_stencil.group(1)
            stencil_val = stencil_abbr.get(stencil_full, stencil_full)
            order_val = m_stencil.group(2)
        else:
            stencil_val = "-"
            order_val = "-"

        # Only include selected columns in each row
        col_val_map = {
            "test": html.Td(test_val, style={"textAlign": "center"}),
            "cg": html.Td(cg_val, style={"textAlign": "center"}),
            "stencil": html.Td(stencil_val, style={"textAlign": "center"}),
            "order": html.Td(order_val, style={"textAlign": "center"}),
            "res": html.Td(res_display, style={"textAlign": "center"}),
            "pml": html.Td(pml_val, style={"textAlign": "center"}),
            "response": response_cell,
        }
        row_children = [col_val_map[c] for c in selected_columns]
        rows.append(html.Tr(row_children))

    table = dbc.Table(
        [header, html.Tbody(rows)],
        bordered=True,
        hover=True,
        size="sm",
        responsive=True,
        style={"padding": "0", "margin": "0", "borderCollapse": "collapse"},
        className="table-compact"
    )
    return html.Div([stencil_legend, table]), grouped, base_order


@app.callback(
    Output("dataset-selection-store", "data"),
    [Input("clear-dataset-button", "n_clicks"),
     Input({"type": "dataset-elastic", "base": ALL}, "value"),
     Input({"type": "dataset-anelastic", "base": ALL}, "value")],
    [State("dataset-selection-store", "data")],
    prevent_initial_call=True,
)
def persist_dataset_selection(clear_clicks, elastic_values, anelastic_values, selection_store):
    triggered_id = ctx.triggered_id if ctx else None
    if not triggered_id:
        raise PreventUpdate
    if triggered_id == "clear-dataset-button":
        return {}
    if not isinstance(triggered_id, dict):
        raise PreventUpdate
    variant = VARIANT_ELASTIC if triggered_id.get("type") == "dataset-elastic" else VARIANT_ANELASTIC
    base = triggered_id.get("base")
    if not base:
        raise PreventUpdate
    payload = bool(ctx.triggered[0]["value"])
    store = dict(selection_store or {})
    entry = store.setdefault(base, {})
    entry[variant] = payload
    return store

@app.callback(
    Output("line-properties-store", "data"),
    [Input({"type": "width", "dataset": ALL}, "value"),
     Input({"type": "dash", "dataset": ALL}, "value"),
     Input({"type": "color", "dataset": ALL}, "value")],
    State("line-properties-store", "data"),
    prevent_initial_call=True,
)
def update_line_properties(width_values, dash_values, color_values, current_props):
    if not current_props: current_props = {}
    triggered = ctx.triggered if ctx else []
    if triggered:
        prop_id = triggered[0]['prop_id']
        import json
        id_dict = json.loads(prop_id.split('.')[0])
        ds, typ, val = id_dict['dataset'], id_dict['type'], triggered[0]['value']
        if ds not in current_props: current_props[ds] = {}
        current_props[ds][typ] = val
    return current_props

@app.callback(
    [Output("plot-container", "children"), Output("line-controls-container", "children")],
    [Input("station-dropdown", "data"),
     Input("plot-checklist", "value"),
     Input({"type": "dataset-elastic", "base": ALL}, "value"),
     Input({"type": "dataset-anelastic", "base": ALL}, "value"),
     Input("plot-height-slider", "value"),
     Input("plot-title-toggle", "value")],
    [State("dataset-path-map", "data"), State("dataset-base-order", "data"), State("line-properties-store", "data")]
)
def update_plot(station, plots_selected, elastic_values, anelastic_values, plot_height, plot_title_toggle, path_map, base_order, properties):
    selected_infos = []
    if base_order and isinstance(path_map, dict):
        for idx, base in enumerate(base_order):
            variants = path_map.get(base, {})
            if idx < len(elastic_values) and elastic_values[idx]:
                p = variants.get(VARIANT_ELASTIC)
                if p:
                    info = parse_dataset_info(Path(p))
                    if info:
                        selected_infos.append(info)
            if idx < len(anelastic_values) and anelastic_values[idx]:
                p = variants.get(VARIANT_ANELASTIC)
                if p:
                    info = parse_dataset_info(Path(p))
                    if info:
                        selected_infos.append(info)

    show_title = plot_title_toggle and "show_title" in plot_title_toggle
    figs = [make_figure(station or "", selected_infos, p, properties, plot_height, show_title=show_title) for p in plots_selected or []]

    label_to_dataset: Dict[str, str] = {}
    for info in selected_infos:
        test_id = parse_test_id(info.dataset)
        label = test_id if test_id else info.dataset
        label_to_dataset[label] = info.dataset
    selected_datasets = sorted(label_to_dataset.keys())
    if selected_datasets:
        rows = []
        for ds in selected_datasets:
            props = properties.get(ds, {})
            dataset_name = label_to_dataset.get(ds, ds)
            default_color = props.get('color') or dataset_color(dataset_name)
            # Line type dropdown replaces opacity slider
            line_type = props.get('dash', 'solid')
            line_type_dropdown = dcc.Dropdown(
                id={"type": "dash", "dataset": ds},
                options=[
                    {"label": "Solid", "value": "solid"},
                    {"label": "Dash", "value": "dash"},
                    {"label": "Dot", "value": "dot"},
                    {"label": "DashDot", "value": "dashdot"},
                    {"label": "LongDash", "value": "longdash"},
                    {"label": "LongDashDot", "value": "longdashdot"}
                ],
                value=line_type,
                clearable=False,
                style={"width": "110px"}
            )
            rows.append(html.Tr([
                html.Td(ds),
                html.Td(dcc.Slider(id={"type": "width", "dataset": ds}, min=1, max=5, value=props.get('width', 2), step=1, marks={1:'1',3:'3',5:'5'})),
                html.Td(line_type_dropdown),
                html.Td(dcc.Input(id={"type": "color", "dataset": ds}, type="color", value=default_color, style={"width": "48px", "height": "32px", "border": "none", "padding": "0"}))
            ]))
        controls = dbc.Table(
            [html.Thead(html.Tr([html.Th("Dataset"), html.Th("Line Width"), html.Th("Line Type"), html.Th("Color")])),
             html.Tbody(rows)],
            bordered=True,
            size="sm",
        )
    else:
        controls = html.Div()
        
    return [dcc.Graph(figure=fig) for fig in figs], controls

# --- 6. EXECUTION ---

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    host = os.environ.get("HOST", "0.0.0.0")
    app.run(host=host, port=port, debug=False)
