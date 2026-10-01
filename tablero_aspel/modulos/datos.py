"""
Modelo de datos: limpia las tablas crudas de Aspel SAE y las une.

Es el mismo trabajo que harían los alumnos en Power Query:
  1. Quitar espacios de las claves (Aspel rellena las claves con espacios).
  2. Convertir textos a números y fechas.
  3. Unir encabezados con partidas, clientes y artículos.
  4. Calcular columnas nuevas (venta neta, margen, días de ciclo).

Convenciones de Aspel SAE usadas aquí:
  - STATUS = 'C' significa documento cancelado.
  - CAN_TOT es el subtotal antes de descuentos e impuestos.
  - DES_TOT y DES_FIN son descuentos; IMPORTE es el total con impuestos.
  - TIP_DOC_SIG / DOC_SIG indican el documento al que pasó un pedido.
"""
import pandas as pd
import streamlit as st

from modulos.conexion import leer_tabla

ESTATUS_CANCELADO = "C"


# ---------------------------------------------------------------------------
# Utilidades de limpieza
# ---------------------------------------------------------------------------
def _col(df: pd.DataFrame, nombre: str, defecto=None) -> pd.Series:
    """Devuelve una columna si existe; si no, una columna con el valor por defecto."""
    if nombre in df.columns:
        return df[nombre]
    return pd.Series(defecto, index=df.index)


def _texto(serie: pd.Series) -> pd.Series:
    """Quita espacios al inicio y al final; los vacíos quedan como texto vacío."""
    return serie.astype("string").str.strip().fillna("")


def _numero(serie: pd.Series) -> pd.Series:
    return pd.to_numeric(serie, errors="coerce").fillna(0.0).astype(float)


def _fecha(serie: pd.Series) -> pd.Series:
    return pd.to_datetime(serie, errors="coerce")


# ---------------------------------------------------------------------------
# Limpieza de cada tabla
# ---------------------------------------------------------------------------
def _clientes(df):
    return pd.DataFrame({
        "cliente": _texto(_col(df, "clave")),
        "nombre": _texto(_col(df, "nombre")),
        "municipio": _texto(_col(df, "municipio")),
        "estado": _texto(_col(df, "estado")).str.title(),
        "zona": _texto(_col(df, "cve_zona")),
        "vendedor": _texto(_col(df, "cve_vend")),
        "limite_credito": _numero(_col(df, "limcred")),
        "dias_credito": _numero(_col(df, "diascred")),
        "saldo": _numero(_col(df, "saldo")),
        "estatus": _texto(_col(df, "status")),
    })


def _proveedores(df):
    return pd.DataFrame({
        "proveedor": _texto(_col(df, "clave")),
        "nombre_proveedor": _texto(_col(df, "nombre")),
        "estado": _texto(_col(df, "estado")).str.title(),
    })


def _articulos(df):
    out = pd.DataFrame({
        "articulo": _texto(_col(df, "cve_art")),
        "descripcion": _texto(_col(df, "descr")),
        "linea": _texto(_col(df, "lin_prod")),
        "unidad": _texto(_col(df, "uni_med")),
        "existencia": _numero(_col(df, "exist")),
        "stock_min": _numero(_col(df, "stock_min")),
        "stock_max": _numero(_col(df, "stock_max")),
        "costo_promedio": _numero(_col(df, "costo_prom")),
        "ultimo_costo": _numero(_col(df, "ult_costo")),
        "ultima_venta": _fecha(_col(df, "fch_ultvta")),
        "estatus": _texto(_col(df, "status")),
    })
    out["linea"] = out["linea"].replace("", "Sin línea")
    out["valor_inventario"] = out["existencia"].clip(lower=0) * out["costo_promedio"]
    return out


def _existencias_almacen(df):
    return pd.DataFrame({
        "articulo": _texto(_col(df, "cve_art")),
        "almacen": _texto(_col(df, "cve_alm")),
        "existencia": _numero(_col(df, "exist")),
        "stock_min": _numero(_col(df, "stock_min")),
    })


def _encabezados_venta(df):
    """Encabezados de facturas o pedidos (misma estructura en Aspel)."""
    out = pd.DataFrame({
        "documento": _texto(_col(df, "cve_doc")),
        "cliente": _texto(_col(df, "cve_clpv")),
        "estatus": _texto(_col(df, "status")),
        "fecha": _fecha(_col(df, "fecha_doc")),
        "fecha_entrega": _fecha(_col(df, "fecha_ent")),
        "subtotal": _numero(_col(df, "can_tot")),
        "descuentos": _numero(_col(df, "des_tot")) + _numero(_col(df, "des_fin")),
        "total": _numero(_col(df, "importe")),
        "vendedor": _texto(_col(df, "cve_vend")),
        "tipo_sig": _texto(_col(df, "tip_doc_sig")),
        "doc_sig": _texto(_col(df, "doc_sig")),
        "tipo_ant": _texto(_col(df, "tip_doc_ant")),
        "doc_ant": _texto(_col(df, "doc_ant")),
        "tipo_cambio": _numero(_col(df, "tipcamb", 1)),
    })
    # Convertir a pesos si el documento está en otra moneda.
    tc = out["tipo_cambio"].where(out["tipo_cambio"] > 0, 1.0)
    out["venta_neta"] = ((out["subtotal"] - out["descuentos"]).clip(lower=0)) * tc
    out["cancelado"] = out["estatus"].eq(ESTATUS_CANCELADO)
    return out


def _partidas(df, columna_cantidad_pendiente=None):
    out = pd.DataFrame({
        "documento": _texto(_col(df, "cve_doc")),
        "articulo": _texto(_col(df, "cve_art")),
        "cantidad": _numero(_col(df, "cant")),
        "precio": _numero(_col(df, "prec")),
        "costo": _numero(_col(df, "cost")),
        "descuento_pct": _numero(_col(df, "desc1")),
        "total_partida": _numero(_col(df, "tot_partida")),
    })
    bruto = out["cantidad"] * out["precio"]
    out["importe"] = bruto * (1 - out["descuento_pct"].clip(0, 100) / 100)
    out["costo_total"] = out["cantidad"] * out["costo"]
    return out


def _compras(df):
    out = pd.DataFrame({
        "documento": _texto(_col(df, "cve_doc")),
        "proveedor": _texto(_col(df, "cve_clpv")),
        "estatus": _texto(_col(df, "status")),
        "fecha": _fecha(_col(df, "fecha_doc")),
        "fecha_recepcion": _fecha(_col(df, "fecha_rec")),
        "subtotal": _numero(_col(df, "can_tot")),
        "descuentos": _numero(_col(df, "des_tot")) + _numero(_col(df, "des_fin")),
        "total": _numero(_col(df, "importe")),
        "tipo_cambio": _numero(_col(df, "tipcamb", 1)),
    })
    tc = out["tipo_cambio"].where(out["tipo_cambio"] > 0, 1.0)
    out["compra_neta"] = ((out["subtotal"] - out["descuentos"]).clip(lower=0)) * tc
    out["cancelado"] = out["estatus"].eq(ESTATUS_CANCELADO)
    return out


# ---------------------------------------------------------------------------
# Modelo completo (se guarda en caché una hora)
# ---------------------------------------------------------------------------
@st.cache_data(ttl=3600, show_spinner=False)
def cargar_modelo() -> dict:
    clientes = _clientes(leer_tabla("clie02"))
    proveedores = _proveedores(leer_tabla("prov02"))
    articulos = _articulos(leer_tabla("inve02"))
    almacenes = _existencias_almacen(leer_tabla("mult02"))
    facturas = _encabezados_venta(leer_tabla("factf02"))
    pedidos = _encabezados_venta(leer_tabla("factp02"))
    compras = _compras(leer_tabla("compc02"))

    # Partidas de factura con fecha, cliente y artículo.
    part_fac = _partidas(leer_tabla("par_factf02")).merge(
        facturas[["documento", "cliente", "fecha", "cancelado"]],
        on="documento", how="inner",
    ).merge(articulos[["articulo", "descripcion", "linea"]], on="articulo", how="left")
    part_fac["linea"] = part_fac["linea"].fillna("Sin línea")
    part_fac["descripcion"] = part_fac["descripcion"].fillna(part_fac["articulo"])

    # Partidas de compra con fecha y proveedor.
    part_com = _partidas(leer_tabla("par_compc02")).merge(
        compras[["documento", "proveedor", "fecha", "cancelado"]],
        on="documento", how="inner",
    )

    # Facturas con nombre y ubicación del cliente.
    facturas = facturas.merge(
        clientes[["cliente", "nombre", "estado", "municipio"]], on="cliente", how="left"
    )
    facturas["nombre"] = facturas["nombre"].fillna("Cliente " + facturas["cliente"])
    facturas["estado"] = facturas["estado"].fillna("").replace("", "Sin estado")

    compras = compras.merge(proveedores[["proveedor", "nombre_proveedor"]],
                            on="proveedor", how="left")
    compras["nombre_proveedor"] = compras["nombre_proveedor"].fillna(
        "Proveedor " + compras["proveedor"])

    ciclo = _ciclo_pedido_factura(pedidos, facturas)

    return {
        "clientes": clientes, "proveedores": proveedores, "articulos": articulos,
        "almacenes": almacenes, "facturas": facturas, "pedidos": pedidos,
        "partidas_factura": part_fac, "compras": compras,
        "partidas_compra": part_com, "ciclo": ciclo,
    }


def _ciclo_pedido_factura(pedidos, facturas):
    """
    Une cada pedido con la factura que lo surtió.
    Primero por el pedido (DOC_SIG) y, si no, por la factura (DOC_ANT).
    """
    fac = facturas[["documento", "fecha", "cancelado"]].rename(columns={
        "documento": "factura", "fecha": "fecha_factura", "cancelado": "factura_cancelada"})

    p = pedidos.copy()
    p["factura"] = p["doc_sig"].where(p["tipo_sig"].str.upper().eq("F"), "")

    # Respaldo: facturas que dicen venir de un pedido.
    desde_fac = facturas.loc[facturas["tipo_ant"].str.upper().eq("P"),
                             ["doc_ant", "documento"]]
    desde_fac = desde_fac.drop_duplicates("doc_ant").set_index("doc_ant")["documento"]
    faltan = p["factura"].eq("")
    p.loc[faltan, "factura"] = p.loc[faltan, "documento"].map(desde_fac).fillna("")

    p = p.merge(fac, on="factura", how="left")
    p["facturado"] = p["factura"].ne("") & p["fecha_factura"].notna()
    p["dias_a_factura"] = (p["fecha_factura"] - p["fecha"]).dt.days
    p["a_tiempo"] = p["facturado"] & (
        p["fecha_entrega"].isna() | (p["fecha_factura"] <= p["fecha_entrega"]))
    p["destino"] = p["tipo_sig"].str.upper().map(
        {"F": "Factura", "R": "Remisión", "": "Pendiente"}).fillna("Otro")
    return p


def filtrar_periodo(df, inicio, fin, excluir_cancelados=True, columna="fecha"):
    """Filtra por rango de fechas y, opcionalmente, quita documentos cancelados."""
    mascara = df[columna].between(pd.Timestamp(inicio),
                                  pd.Timestamp(fin) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1))
    if excluir_cancelados and "cancelado" in df.columns:
        mascara &= ~df["cancelado"]
    return df.loc[mascara]
