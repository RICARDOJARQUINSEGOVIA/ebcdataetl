"""
Tablero de operaciones con datos reales (anonimizados) de Aspel SAE.

Pestañas: Resumen, Clientes, Pedidos a facturas, Inventario, Compras y Datos.
Para correr en tu computadora:  streamlit run app.py
"""
import pandas as pd
import streamlit as st

from modulos import graficas as g
from modulos.datos import cargar_modelo, filtrar_periodo

st.set_page_config(page_title="Tablero Aspel SAE", page_icon="📦", layout="wide")

st.markdown("""
<style>
  .block-container {padding-top: 2rem; max-width: 1300px;}
  [data-testid="stMetricValue"] {font-size: 1.7rem;}
  [data-testid="stMetric"] {border-left: 3px solid #0F5257; padding-left: .8rem;}
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Carga de datos
# ---------------------------------------------------------------------------
try:
    with st.spinner("Leyendo datos de la base…"):
        m = cargar_modelo()
except KeyError:
    st.error("Falta la configuración de la base de datos. Agrega la sección "
             "[database] con url y esquema en Settings › Secrets.")
    st.stop()
except Exception as error:  # noqa: BLE001
    st.error("No se pudo leer la base de datos. Revisa la url en Secrets y que "
             "el usuario tenga permiso de lectura sobre el esquema.")
    st.caption(f"Detalle técnico: {error}")
    st.stop()

fac_todas = m["facturas"]
if fac_todas["fecha"].notna().sum() == 0:
    st.warning("La tabla de facturas no tiene fechas válidas.")
    st.stop()


# ---------------------------------------------------------------------------
# Barra lateral: periodo y filtros
# ---------------------------------------------------------------------------
fecha_max = fac_todas["fecha"].max().date()
fecha_min = fac_todas["fecha"].min().date()
inicio_defecto = max(fecha_min, (pd.Timestamp(fecha_max) - pd.DateOffset(months=12)).date())

with st.sidebar:
    st.header("Periodo de análisis")
    rango = st.date_input("Fechas", value=(inicio_defecto, fecha_max),
                          min_value=fecha_min, max_value=fecha_max, format="DD/MM/YYYY")
    inicio, fin = (rango if isinstance(rango, tuple) and len(rango) == 2
                   else (inicio_defecto, fecha_max))
    excluir = st.checkbox("Excluir documentos cancelados", value=True)
    st.caption(f"La base tiene datos del {fecha_min:%d/%m/%Y} al {fecha_max:%d/%m/%Y}.")
    st.divider()
    if st.button("Actualizar datos", width="stretch",
                 help="Vuelve a leer la base de datos (como Actualizar todo en Excel)."):
        st.cache_data.clear()
        st.rerun()

fac = filtrar_periodo(m["facturas"], inicio, fin, excluir)
part = filtrar_periodo(m["partidas_factura"], inicio, fin, excluir)
ciclo = filtrar_periodo(m["ciclo"], inicio, fin, excluir)
com = filtrar_periodo(m["compras"], inicio, fin, excluir)
part_com = filtrar_periodo(m["partidas_compra"], inicio, fin, excluir)

st.title("Tablero de operaciones")
st.caption(f"Datos reales anonimizados de Aspel SAE · del {inicio:%d/%m/%Y} al {fin:%d/%m/%Y}")

if fac.empty:
    st.info("No hay facturas en el periodo elegido. Amplía el rango de fechas en la barra lateral.")
    st.stop()

pestanas = st.tabs(["Resumen", "Clientes", "Pedidos a facturas",
                    "Inventario", "Compras", "Datos"])


# ---------------------------------------------------------------------------
# 1. Resumen
# ---------------------------------------------------------------------------
with pestanas[0]:
    venta = fac["venta_neta"].sum()
    n_fac = len(fac)
    costo = part["costo_total"].sum()
    imp_part = part["importe"].sum()
    margen = (imp_part - costo) / imp_part if imp_part and costo else None

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Venta neta (sin IVA)", g.pesos(venta))
    c2.metric("Facturas", g.entero(n_fac))
    c3.metric("Ticket promedio", g.pesos(venta / n_fac))
    c4.metric("Clientes que compraron", g.entero(fac["cliente"].nunique()))

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Margen bruto", g.porcentaje(margen) if margen is not None else "Sin costo")
    c6.metric("Artículos distintos vendidos", g.entero(part["articulo"].nunique()))
    pct_fact = ciclo["facturado"].mean() if len(ciclo) else 0
    c7.metric("Pedidos facturados", g.porcentaje(pct_fact))
    c8.metric("Compras netas", g.pesos(com["compra_neta"].sum()))

    mensual = fac.set_index("fecha").resample("MS")
    st.plotly_chart(g.barras_y_linea(
        mensual["venta_neta"].sum(), mensual["cliente"].nunique(),
        "Venta mensual y clientes activos", "Venta neta", "Clientes activos"),
        width="stretch")

    col_a, col_b = st.columns(2)
    por_linea = part.groupby("linea")["importe"].sum().nlargest(10)
    col_a.plotly_chart(g.barras_horizontales(por_linea, "Venta por línea de producto (top 10)"),
                       width="stretch")
    por_estado = fac.groupby("estado")["venta_neta"].sum().nlargest(10)
    col_b.plotly_chart(g.barras_horizontales(por_estado, "Venta por estado (top 10)",
                                             color=g.AMBAR),
                       width="stretch")


# ---------------------------------------------------------------------------
# 2. Clientes
# ---------------------------------------------------------------------------
with pestanas[1]:
    por_cliente = fac.groupby(["cliente", "nombre"]).agg(
        venta=("venta_neta", "sum"), frecuencia=("documento", "count"),
        ultima=("fecha", "max"), primera=("fecha", "min")).reset_index()
    por_cliente["recencia"] = (pd.Timestamp(fin) - por_cliente["ultima"]).dt.days
    por_cliente = por_cliente.sort_values("venta", ascending=False)

    acumulado = por_cliente["venta"].cumsum() / por_cliente["venta"].sum()
    n80 = int((acumulado < 0.8).sum()) + 1
    pct80 = n80 / len(por_cliente)

    c1, c2, c3 = st.columns(3)
    c1.metric("Clientes que compraron", g.entero(len(por_cliente)))
    c2.metric("Clientes que hacen el 80 % de la venta",
              f"{g.entero(n80)} ({g.porcentaje(pct80)})")
    c3.metric("Facturas por cliente (mediana)", g.entero(por_cliente["frecuencia"].median()))

    col_a, col_b = st.columns(2)
    col_a.plotly_chart(g.pareto(por_cliente.set_index("nombre")["venta"],
                                "Concentración de la venta (Pareto)"),
                       width="stretch")
    top = por_cliente.head(15).set_index("nombre")["venta"]
    col_b.plotly_chart(g.barras_horizontales(top, "Los 15 clientes con más venta"),
                       width="stretch")

    st.plotly_chart(g.dispersion_rfm(por_cliente, "Recencia y frecuencia de compra"),
                    width="stretch")
    st.caption("Arriba a la izquierda: clientes frecuentes y recientes. "
               "Abajo a la derecha: clientes que dejaron de comprar.")

    # Nuevos contra recurrentes: mes de la primera compra en toda la historia.
    primera_hist = m["facturas"].loc[~m["facturas"]["cancelado"]].groupby("cliente")["fecha"].min()
    fac_mes = fac.assign(mes=fac["fecha"].dt.to_period("M").dt.to_timestamp(),
                         primera=fac["cliente"].map(primera_hist))
    fac_mes["tipo"] = (fac_mes["primera"].dt.to_period("M").dt.to_timestamp()
                       .eq(fac_mes["mes"]).map({True: "Nuevos", False: "Recurrentes"}))
    nuevos = (fac_mes.groupby(["mes", "tipo"])["cliente"].nunique()
              .unstack(fill_value=0).reindex(columns=["Nuevos", "Recurrentes"], fill_value=0))
    st.subheader("Clientes nuevos y recurrentes por mes")
    st.bar_chart(nuevos, color=[g.AMBAR, g.PETROLEO], height=300)

    st.subheader("Detalle por cliente")
    st.dataframe(
        por_cliente[["cliente", "nombre", "venta", "frecuencia", "ultima", "recencia"]],
        hide_index=True, width="stretch",
        column_config={
            "venta": st.column_config.NumberColumn("Venta neta", format="$%,.0f"),
            "frecuencia": st.column_config.NumberColumn("Facturas"),
            "ultima": st.column_config.DateColumn("Última compra", format="DD/MM/YYYY"),
            "recencia": st.column_config.NumberColumn("Días sin comprar"),
        })


# ---------------------------------------------------------------------------
# 3. Pedidos a facturas
# ---------------------------------------------------------------------------
with pestanas[2]:
    if ciclo.empty:
        st.info("No hay pedidos en el periodo elegido.")
    else:
        facturados = ciclo.loc[ciclo["facturado"] & ciclo["dias_a_factura"].ge(0)]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Pedidos", g.entero(len(ciclo)))
        c2.metric("Facturados", g.porcentaje(ciclo["facturado"].mean()))
        c3.metric("Días de pedido a factura (mediana)",
                  g.entero(facturados["dias_a_factura"].median()) if len(facturados) else "—")
        c4.metric("Facturados a tiempo",
                  g.porcentaje(facturados["a_tiempo"].mean()) if len(facturados) else "—",
                  help="Factura emitida en o antes de la fecha de entrega del pedido.")

        col_a, col_b = st.columns(2)
        if len(facturados):
            col_a.plotly_chart(g.histograma(facturados["dias_a_factura"].clip(upper=60),
                                            "Días entre pedido y factura",
                                            "Días (60 o más se agrupan al final)"),
                               width="stretch")
        destino = ciclo["destino"].value_counts()
        col_b.plotly_chart(g.barras_horizontales(destino, "¿A qué documento pasó cada pedido?",
                                                 color=g.GRIS, prefijo=""),
                           width="stretch")
        st.caption("Si muchos pedidos pasan a remisión, se facturan después desde la "
                   "remisión; esas remisiones no están en esta base.")

        mensual = ciclo.set_index("fecha").resample("MS")["facturado"].mean()
        st.plotly_chart(g.barras_mensuales(mensual * 100, "Porcentaje de pedidos facturados por mes",
                                           prefijo=""), width="stretch")

        pendientes = ciclo.loc[~ciclo["facturado"] & ciclo["destino"].eq("Pendiente")]
        st.subheader(f"Pedidos sin surtir ({len(pendientes):,})")
        st.dataframe(
            pendientes[["documento", "cliente", "fecha", "fecha_entrega", "venta_neta"]]
            .sort_values("fecha"),
            hide_index=True, width="stretch",
            column_config={
                "fecha": st.column_config.DateColumn("Fecha pedido", format="DD/MM/YYYY"),
                "fecha_entrega": st.column_config.DateColumn("Entrega comprometida",
                                                             format="DD/MM/YYYY"),
                "venta_neta": st.column_config.NumberColumn("Importe", format="$%,.0f"),
            })


# ---------------------------------------------------------------------------
# 4. Inventario
# ---------------------------------------------------------------------------
with pestanas[3]:
    art = m["articulos"]
    activos = art.loc[art["estatus"].ne("B")]
    bajo_min = activos.loc[(activos["stock_min"] > 0) & (activos["existencia"] < activos["stock_min"])]
    vendidos = set(part["articulo"])
    sin_venta = activos.loc[(activos["existencia"] > 0) & ~activos["articulo"].isin(vendidos)]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Valor del inventario (hoy)", g.pesos(activos["valor_inventario"].sum()))
    c2.metric("Artículos con existencia", g.entero((activos["existencia"] > 0).sum()))
    c3.metric("Bajo su mínimo", g.entero(len(bajo_min)))
    c4.metric("Con existencia pero sin venta en el periodo", g.entero(len(sin_venta)),
              help="Inventario que no se movió en las fechas elegidas.")

    # Clasificación ABC por venta del periodo.
    venta_art = part.groupby("articulo")["importe"].sum().sort_values(ascending=False)
    if venta_art.sum() > 0:
        acum = venta_art.cumsum() / venta_art.sum()
        abc = pd.cut(acum, [0, 0.8, 0.95, 1.0001], labels=["A", "B", "C"])
        resumen_abc = pd.DataFrame({"Artículos": abc.value_counts().sort_index(),
                                    "Venta": venta_art.groupby(abc, observed=False).sum()})
        resumen_abc["% de la venta"] = resumen_abc["Venta"] / resumen_abc["Venta"].sum()
        col_a, col_b = st.columns([1, 2])
        col_a.subheader("Clasificación ABC")
        col_a.dataframe(resumen_abc, width="stretch", column_config={
            "Venta": st.column_config.NumberColumn(format="$%,.0f"),
            "% de la venta": st.column_config.NumberColumn(format="percent")})
        col_a.caption("A: artículos que suman el 80 % de la venta. B: el siguiente 15 %. C: el resto.")
        valor_linea = activos.groupby("linea")["valor_inventario"].sum().nlargest(12)
        col_b.plotly_chart(g.barras_horizontales(valor_linea, "Valor del inventario por línea"),
                           width="stretch")

    alm = m["almacenes"].groupby("almacen")["existencia"].sum()
    if len(alm) > 1:
        st.plotly_chart(g.barras_horizontales(alm, "Unidades en existencia por almacén",
                                              color=g.GRIS, prefijo=""),
                        width="stretch")

    st.subheader(f"Artículos bajo su mínimo ({len(bajo_min):,})")
    st.dataframe(
        bajo_min[["articulo", "descripcion", "linea", "existencia", "stock_min", "stock_max"]]
        .assign(faltante=lambda d: d["stock_min"] - d["existencia"])
        .sort_values("faltante", ascending=False),
        hide_index=True, width="stretch")


# ---------------------------------------------------------------------------
# 5. Compras
# ---------------------------------------------------------------------------
with pestanas[4]:
    if com.empty:
        st.info("No hay compras en el periodo elegido.")
    else:
        recibidas = com.loc[com["fecha_recepcion"].notna()]
        dias_rec = (recibidas["fecha_recepcion"] - recibidas["fecha"]).dt.days
        dias_rec = dias_rec[dias_rec >= 0]

        c1, c2, c3 = st.columns(3)
        c1.metric("Compras netas", g.pesos(com["compra_neta"].sum()))
        c2.metric("Documentos de compra", g.entero(len(com)))
        c3.metric("Proveedores", g.entero(com["proveedor"].nunique()))

        st.plotly_chart(g.barras_mensuales(com.set_index("fecha").resample("MS")["compra_neta"].sum(),
                                           "Compras mensuales", color=g.AMBAR),
                        width="stretch")

        col_a, col_b = st.columns(2)
        top_prov = com.groupby("nombre_proveedor")["compra_neta"].sum().nlargest(12)
        col_a.plotly_chart(g.barras_horizontales(top_prov, "Proveedores con más compra",
                                                 color=g.AMBAR),
                           width="stretch")
        if len(dias_rec) and dias_rec.max() > 0:
            col_b.plotly_chart(g.histograma(dias_rec.clip(upper=60),
                                            "Días entre la compra y su recepción", "Días",
                                            color=g.AMBAR),
                               width="stretch")

        # Comparar lo que se compró contra lo que se vendió por artículo.
        cmp = pd.DataFrame({
            "Comprado (unidades)": part_com.groupby("articulo")["cantidad"].sum(),
            "Vendido (unidades)": part.groupby("articulo")["cantidad"].sum(),
        }).fillna(0)
        cmp["Diferencia"] = cmp["Comprado (unidades)"] - cmp["Vendido (unidades)"]
        cmp = cmp.join(m["articulos"].set_index("articulo")[["descripcion"]])
        st.subheader("Compra contra venta por artículo")
        st.caption("Diferencias grandes y positivas: se compró más de lo que se vendió.")
        st.dataframe(cmp.sort_values("Diferencia", ascending=False)
                     [["descripcion", "Comprado (unidades)", "Vendido (unidades)", "Diferencia"]],
                     width="stretch")


# ---------------------------------------------------------------------------
# 6. Datos (consulta y descarga)
# ---------------------------------------------------------------------------
with pestanas[5]:
    st.write("Tablas ya limpias y unidas, listas para descargar y practicar en Excel.")
    opciones = {
        "Facturas": fac, "Partidas de factura": part, "Pedidos y su factura": ciclo,
        "Clientes": m["clientes"], "Artículos": m["articulos"],
        "Existencias por almacén": m["almacenes"], "Compras": com,
    }
    eleccion = st.selectbox("Tabla", list(opciones))
    datos = opciones[eleccion]
    st.caption(f"{len(datos):,} filas")
    st.dataframe(datos.head(1000), hide_index=True, width="stretch")
    st.download_button(f"Descargar {eleccion.lower()} (CSV)",
                       datos.to_csv(index=False).encode("utf-8-sig"),
                       file_name=f"{eleccion.lower().replace(' ', '_')}.csv",
                       mime="text/csv")
