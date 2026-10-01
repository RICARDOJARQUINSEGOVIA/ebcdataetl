"""Gráficas (Plotly) y formatos de número con un estilo común."""
import pandas as pd
import plotly.graph_objects as go

TINTA = "#16323A"
PETROLEO = "#0F5257"
AMBAR = "#C98A1B"
GRIS = "#8A9A9E"
FONDO = "rgba(0,0,0,0)"


def pesos(valor: float) -> str:
    """$1,234,567 con abreviatura para millones."""
    if abs(valor) >= 1_000_000:
        return f"${valor / 1_000_000:,.1f} M"
    return f"${valor:,.0f}"


def entero(valor: float) -> str:
    return f"{valor:,.0f}"


def porcentaje(valor: float) -> str:
    return f"{valor:.1%}"


def _estilo(fig: go.Figure, alto=340, titulo=None) -> go.Figure:
    fig.update_layout(
        title=dict(text=titulo, x=0, font=dict(size=15, color=TINTA)) if titulo else None,
        height=alto, margin=dict(l=10, r=10, t=45 if titulo else 10, b=10),
        paper_bgcolor=FONDO, plot_bgcolor=FONDO,
        font=dict(color=TINTA, size=12),
        legend=dict(orientation="h", yanchor="top", y=-0.15, x=0),
        hoverlabel=dict(bgcolor="white"),
    )
    fig.update_xaxes(showgrid=False, linecolor="#C9D3D5")
    fig.update_yaxes(gridcolor="#E3E9EA", zeroline=False)
    return fig


def barras_mensuales(serie: pd.Series, titulo: str, color=PETROLEO, prefijo="$"):
    fig = go.Figure(go.Bar(
        x=serie.index, y=serie.values, marker_color=color,
        hovertemplate=f"%{{x|%b %Y}}<br>{prefijo}%{{y:,.0f}}<extra></extra>"))
    fig.update_yaxes(tickprefix=prefijo, separatethousands=True)
    return _estilo(fig, titulo=titulo)


def barras_y_linea(barras: pd.Series, linea: pd.Series, titulo: str,
                   nombre_barras: str, nombre_linea: str):
    """Barras en el eje izquierdo y una línea en el derecho."""
    fig = go.Figure()
    fig.add_bar(x=barras.index, y=barras.values, name=nombre_barras,
                marker_color=PETROLEO,
                hovertemplate="%{x|%b %Y}<br>$%{y:,.0f}<extra></extra>")
    fig.add_scatter(x=linea.index, y=linea.values, name=nombre_linea, yaxis="y2",
                    mode="lines+markers", line=dict(color=AMBAR, width=2.5),
                    hovertemplate="%{x|%b %Y}<br>%{y:,.0f}<extra></extra>")
    fig.update_layout(yaxis=dict(tickprefix="$", separatethousands=True),
                      yaxis2=dict(overlaying="y", side="right", showgrid=False))
    return _estilo(fig, titulo=titulo)


def barras_horizontales(serie: pd.Series, titulo: str, color=PETROLEO,
                        prefijo="$", alto=None):
    serie = serie.sort_values()
    fig = go.Figure(go.Bar(
        x=serie.values, y=serie.index.astype(str), orientation="h", marker_color=color,
        hovertemplate=f"%{{y}}<br>{prefijo}%{{x:,.0f}}<extra></extra>"))
    fig.update_xaxes(tickprefix=prefijo, separatethousands=True)
    return _estilo(fig, alto=alto or max(300, 24 * len(serie) + 60), titulo=titulo)


def pareto(ventas_por_cliente: pd.Series, titulo: str):
    """Curva acumulada: qué porcentaje de clientes genera qué porcentaje de la venta."""
    s = ventas_por_cliente.sort_values(ascending=False)
    acumulado = s.cumsum() / s.sum()
    x = (pd.Series(range(1, len(s) + 1)) / len(s)).values
    fig = go.Figure()
    fig.add_scatter(x=x, y=acumulado.values, mode="lines", line=dict(color=PETROLEO, width=3),
                    fill="tozeroy", fillcolor="rgba(15,82,87,0.12)",
                    hovertemplate="%{x:.0%} de los clientes<br>%{y:.0%} de la venta<extra></extra>")
    fig.add_hline(y=0.8, line=dict(color=AMBAR, dash="dash"),
                  annotation_text="80 % de la venta", annotation_position="bottom right")
    fig.update_xaxes(tickformat=".0%", title="Clientes (de mayor a menor compra)")
    fig.update_yaxes(tickformat=".0%", title="Venta acumulada", range=[0, 1.02])
    return _estilo(fig, alto=360, titulo=titulo)


def histograma(valores: pd.Series, titulo: str, eje_x: str, color=PETROLEO):
    fig = go.Figure(go.Histogram(x=valores, marker_color=color, nbinsx=30,
                                 hovertemplate="%{x}<br>%{y} documentos<extra></extra>"))
    fig.update_xaxes(title=eje_x)
    fig.update_yaxes(title="Documentos")
    return _estilo(fig, titulo=titulo)


def dispersion_rfm(tabla: pd.DataFrame, titulo: str):
    """Recencia (días desde la última compra) contra frecuencia, tamaño = venta."""
    tamano = (tabla["venta"] / tabla["venta"].max() * 40).clip(lower=4)
    fig = go.Figure(go.Scatter(
        x=tabla["recencia"], y=tabla["frecuencia"], mode="markers",
        marker=dict(size=tamano, color=PETROLEO, opacity=0.55, line=dict(width=0)),
        text=tabla["nombre"],
        customdata=tabla["venta"],
        hovertemplate="%{text}<br>Última compra hace %{x} días<br>"
                      "%{y} facturas<br>$%{customdata:,.0f}<extra></extra>"))
    fig.update_xaxes(title="Días desde la última compra")
    fig.update_yaxes(title="Número de facturas", type="log")
    return _estilo(fig, alto=380, titulo=titulo)
