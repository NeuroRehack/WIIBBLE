"""WIIBBLE Posturographic Report Generator.

Produces a fully self-contained, offline interactive HTML report for a single
WIIBBLE recording session.  All Plotly charts are embedded directly in the HTML
(no CDN dependency).

Usage
-----
    python report.py <csv_path> [--features <json_path>] [--out <html_path>]

    python report.py recordings/recording_20260420_130030.csv
    python report.py recordings/recording_20260420_130030.csv \\
        --features recordings/features_20260420_130030.json \\
        --out recordings/my_report.html

If ``--features`` is omitted the script looks for a ``features_*.json`` file
whose timestamp matches the CSV filename.  If none is found the feature-based
sections (radar chart and feature table) are omitted from the report.

Output
------
A single ``.html`` file written to the same directory as the CSV (or to
``--out``) that can be opened in any modern browser.  Use the browser's
Print → Save as PDF for a portable copy.
"""

from __future__ import annotations

import argparse
import datetime
import json
import logging
import os
import re
import sys
import time

import numpy as np
import plotly.graph_objects as go
from jinja2 import Template
from plotly.subplots import make_subplots

from analysis import load_recording, to_cop_array
from code_descriptors_postural_control.stabilogram.stato import Stabilogram

start_all = time.time()
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger(__name__)
log.info("Starting WIIBBLE report generation script…")
log.info("Importing scientific libraries (this may take several seconds the first time)…")

log.info("Imports complete.")

log.info("Importing WIIBBLE analysis modules…")

log.info("WIIBBLE analysis code imported.")


# ---------------------------------------------------------------------------
# Colour palette — consistent across all charts
# ---------------------------------------------------------------------------
_COL_ML = "#4C72B0"  # blue  — mediolateral
_COL_AP = "#DD8452"  # orange — anteroposterior
_COL_ELLIPSE = "#C44E52"  # red   — 95 % confidence ellipse
_COL_BAND1 = "rgba(100,180,100,0.15)"  # 0–1 Hz band
_COL_BAND2 = "rgba(220,100,100,0.15)"  # 1–3 Hz band

# ---------------------------------------------------------------------------
# Chart helpers
# ---------------------------------------------------------------------------


def _base_layout(**kwargs) -> dict:
    """Shared layout defaults — clean, white, clinical look."""
    base = dict(
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(family="Arial, sans-serif", size=13, color="#333"),
        margin=dict(l=60, r=30, t=50, b=50),
    )
    base.update(kwargs)
    return base


def _fig_html(fig: go.Figure, first: bool = False) -> str:
    """Serialise a Plotly figure to an HTML div string."""
    return fig.to_html(
        full_html=False,
        include_plotlyjs=first,  # bundle embedded only in the first figure
        config={"responsive": True, "displayModeBar": True},
    )


# ---------------------------------------------------------------------------
# 1. CoP Sway Path + 95 % Confidence Ellipse
# ---------------------------------------------------------------------------


def plot_sway_path(stab: Stabilogram, features: dict | None) -> go.Figure:
    ml = stab.medio_lateral.flatten()
    ap = stab.antero_posterior.flatten()

    fig = go.Figure()

    # Sway trail
    fig.add_trace(
        go.Scatter(
            x=ml,
            y=ap,
            mode="lines",
            line=dict(color=_COL_ML, width=0.8),
            opacity=0.6,
            name="Sway path",
            hovertemplate="ML: %{x:.2f} cm<br>AP: %{y:.2f} cm<extra></extra>",
        )
    )

    # Start / end markers
    fig.add_trace(
        go.Scatter(
            x=[ml[0]],
            y=[ap[0]],
            mode="markers",
            marker=dict(size=10, color="green", symbol="circle"),
            name="Start",
            hovertemplate="Start<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[ml[-1]],
            y=[ap[-1]],
            mode="markers",
            marker=dict(size=10, color="red", symbol="x"),
            name="End",
            hovertemplate="End<extra></extra>",
        )
    )

    # 95 % confidence ellipse from covariance
    cov = np.cov(ml, ap)
    eigenvalues, eigenvectors = np.linalg.eigh(cov)
    chi2_val = 5.991  # chi-squared, 2 DOF, 95 %
    t = np.linspace(0, 2 * np.pi, 300)
    ellipse = (
        np.sqrt(chi2_val)
        * eigenvectors
        @ np.diag(np.sqrt(np.abs(eigenvalues)))
        @ np.array([np.cos(t), np.sin(t)])
    )
    fig.add_trace(
        go.Scatter(
            x=ellipse[0] + np.mean(ml),
            y=ellipse[1] + np.mean(ap),
            mode="lines",
            line=dict(color=_COL_ELLIPSE, width=2, dash="dash"),
            name="95% ellipse",
            hoverinfo="skip",
        )
    )

    ellipse_area = features.get("confidence_ellipse_area_ML_AND_AP") if features else None
    title_suffix = f"  |  Ellipse area: {ellipse_area:.2f} cm²" if ellipse_area is not None else ""

    fig.update_layout(
        **_base_layout(
            title=f"CoP Sway Path + 95% Confidence Ellipse{title_suffix}",
            xaxis=dict(
                title="Mediolateral (cm)", zeroline=True, zerolinecolor="#ccc", gridcolor="#eee"
            ),
            yaxis=dict(
                title="Anteroposterior (cm)",
                zeroline=True,
                zerolinecolor="#ccc",
                gridcolor="#eee",
                scaleanchor="x",
                scaleratio=1,
            ),
            legend=dict(orientation="h", y=-0.15),
        )
    )
    return fig


# ---------------------------------------------------------------------------
# 2. ML / AP Time Series
# ---------------------------------------------------------------------------


def plot_time_series(stab: Stabilogram) -> go.Figure:
    ml = stab.medio_lateral.flatten()
    ap = stab.antero_posterior.flatten()
    t = np.arange(len(ml)) / stab.frequency

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        subplot_titles=("Mediolateral (ML)", "Anteroposterior (AP)"),
        vertical_spacing=0.1,
    )

    fig.add_trace(
        go.Scatter(
            x=t,
            y=ml,
            mode="lines",
            line=dict(color=_COL_ML, width=1),
            name="ML",
            hovertemplate="t=%{x:.2f}s  ML=%{y:.2f}cm<extra></extra>",
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=t,
            y=ap,
            mode="lines",
            line=dict(color=_COL_AP, width=1),
            name="AP",
            hovertemplate="t=%{x:.2f}s  AP=%{y:.2f}cm<extra></extra>",
        ),
        row=2,
        col=1,
    )

    # Zero reference lines
    for row in (1, 2):
        fig.add_hline(y=0, line=dict(color="#aaa", width=1, dash="dot"), row=row, col=1)

    fig.update_xaxes(title_text="Time (s)", row=2, col=1, gridcolor="#eee")
    fig.update_yaxes(title_text="Displacement (cm)", gridcolor="#eee")
    fig.update_layout(**_base_layout(title="CoP Time Series — ML and AP Channels"))
    return fig


# ---------------------------------------------------------------------------
# 3. CoP Velocity Time Series
# ---------------------------------------------------------------------------


def plot_velocity(stab: Stabilogram) -> go.Figure:
    speed = stab.speed  # shape (N, 2) — ML, AP
    ml_v = speed[:, 0]
    ap_v = speed[:, 1]
    t = np.arange(len(ml_v)) / stab.frequency

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        subplot_titles=("ML Velocity", "AP Velocity"),
        vertical_spacing=0.1,
    )

    fig.add_trace(
        go.Scatter(
            x=t,
            y=ml_v,
            mode="lines",
            line=dict(color=_COL_ML, width=1),
            name="ML velocity",
            hovertemplate="t=%{x:.2f}s  v=%{y:.3f}cm/s<extra></extra>",
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=t,
            y=ap_v,
            mode="lines",
            line=dict(color=_COL_AP, width=1),
            name="AP velocity",
            hovertemplate="t=%{x:.2f}s  v=%{y:.3f}cm/s<extra></extra>",
        ),
        row=2,
        col=1,
    )

    for row in (1, 2):
        fig.add_hline(y=0, line=dict(color="#aaa", width=1, dash="dot"), row=row, col=1)

    fig.update_xaxes(title_text="Time (s)", row=2, col=1, gridcolor="#eee")
    fig.update_yaxes(title_text="Velocity (cm/s)", gridcolor="#eee")
    fig.update_layout(**_base_layout(title="CoP Velocity Time Series"))
    return fig


# ---------------------------------------------------------------------------
# 4. Power Spectral Density
# ---------------------------------------------------------------------------


def plot_psd(stab: Stabilogram, features: dict | None) -> go.Figure:
    ps = stab.power_spectrum  # shape (N, 3) — [freq, PSD_ML, PSD_AP]
    freqs = ps[:, 0]
    psd_ml = ps[:, 1]
    psd_ap = ps[:, 2]

    # Crop display to 0–5 Hz (clinically relevant range)
    mask = freqs <= 5.0
    freqs = freqs[mask]
    psd_ml = psd_ml[mask]
    psd_ap = psd_ap[mask]

    fig = go.Figure()

    # Frequency bands
    for x0, x1, color, label in [
        (0.0, 1.0, _COL_BAND1, "0–1 Hz (normal sway)"),
        (1.0, 3.0, _COL_BAND2, "1–3 Hz (elevated concern)"),
    ]:
        fig.add_vrect(
            x0=x0,
            x1=x1,
            fillcolor=color,
            line_width=0,
            annotation_text=label,
            annotation_position="top left",
            annotation=dict(font_size=11, font_color="#666"),
        )

    fig.add_trace(
        go.Scatter(
            x=freqs,
            y=psd_ml,
            mode="lines",
            fill="tozeroy",
            fillcolor="rgba(76,114,176,0.2)",
            line=dict(color=_COL_ML, width=1.5),
            name="ML PSD",
            hovertemplate="f=%{x:.3f}Hz  PSD=%{y:.4f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=freqs,
            y=psd_ap,
            mode="lines",
            fill="tozeroy",
            fillcolor="rgba(221,132,82,0.2)",
            line=dict(color=_COL_AP, width=1.5),
            name="AP PSD",
            hovertemplate="f=%{x:.3f}Hz  PSD=%{y:.4f}<extra></extra>",
        )
    )

    # Annotate 95 % power frequencies if available
    if features:
        for key, color, label in [
            ("power_frequency_95_Power_Spectrum_Density_ML", _COL_ML, "f95 ML"),
            ("power_frequency_95_Power_Spectrum_Density_AP", _COL_AP, "f95 AP"),
        ]:
            val = features.get(key)
            if val is not None:
                fig.add_vline(
                    x=val,
                    line=dict(color=color, width=1, dash="dash"),
                    annotation_text=f"{label}={val:.2f}Hz",
                    annotation_position="top right",
                    annotation=dict(font_size=10),
                )

    fig.update_layout(
        **_base_layout(
            title="Power Spectral Density (Welch method)",
            xaxis=dict(title="Frequency (Hz)", gridcolor="#eee"),
            yaxis=dict(title="PSD (cm² / Hz)", gridcolor="#eee"),
            legend=dict(orientation="h", y=-0.15),
        )
    )
    return fig


# ---------------------------------------------------------------------------
# 5. Diffusion Plot (log-log MSD)
# ---------------------------------------------------------------------------


def plot_diffusion(stab: Stabilogram, features: dict | None) -> go.Figure:
    dp = stab.diffusion_plot  # shape (N, 3) — [time, MSD_ML, MSD_AP]
    t = dp[:, 0]
    msd_ml = dp[:, 1]
    msd_ap = dp[:, 2]

    # Drop t=0 row to avoid log(0)
    mask = t > 0
    t = t[mask]
    msd_ml = msd_ml[mask]
    msd_ap = msd_ap[mask]

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=t,
            y=msd_ml,
            mode="lines",
            line=dict(color=_COL_ML, width=2),
            name="MSD ML",
            hovertemplate="Δt=%{x:.2f}s  MSD=%{y:.4f}cm²<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=t,
            y=msd_ap,
            mode="lines",
            line=dict(color=_COL_AP, width=2),
            name="MSD AP",
            hovertemplate="Δt=%{x:.2f}s  MSD=%{y:.4f}cm²<extra></extra>",
        )
    )

    # Mark critical times if available
    if features:
        for key, color, label in [
            ("critical_time_Diffusion_ML", _COL_ML, "t* ML"),
            ("critical_time_Diffusion_AP", _COL_AP, "t* AP"),
        ]:
            val = features.get(key)
            if val is not None:
                fig.add_vline(
                    x=val,
                    line=dict(color=color, width=1.2, dash="dash"),
                    annotation_text=f"{label}={val:.2f}s",
                    annotation_position="top left",
                    annotation=dict(font_size=10),
                )

    fig.update_layout(
        **_base_layout(
            title="Diffusion Plot — Mean Square Displacement (log-log)",
            xaxis=dict(title="Time interval Δt (s)", type="log", gridcolor="#eee"),
            yaxis=dict(title="MSD (cm²)", type="log", gridcolor="#eee"),
            legend=dict(orientation="h", y=-0.15),
        )
    )
    return fig


# ---------------------------------------------------------------------------
# 6. CoP Density Heatmap (2D histogram contour)
# ---------------------------------------------------------------------------


def plot_density_heatmap(stab: Stabilogram) -> go.Figure:
    ml = stab.medio_lateral.flatten()
    ap = stab.antero_posterior.flatten()

    fig = go.Figure()

    fig.add_trace(
        go.Histogram2dContour(
            x=ml,
            y=ap,
            colorscale="Blues",
            reversescale=False,
            showscale=True,
            colorbar=dict(title="Density"),
            contours=dict(showlabels=True, labelfont=dict(size=10, color="white")),
            hovertemplate="ML: %{x:.2f} cm<br>AP: %{y:.2f} cm<extra></extra>",
            name="Density",
        )
    )

    # Overlay sway path faintly
    fig.add_trace(
        go.Scatter(
            x=ml,
            y=ap,
            mode="lines",
            line=dict(color="rgba(80,80,80,0.2)", width=0.5),
            showlegend=False,
            hoverinfo="skip",
        )
    )

    # Centre crosshair
    fig.add_hline(y=0, line=dict(color="#aaa", width=1, dash="dot"))
    fig.add_vline(x=0, line=dict(color="#aaa", width=1, dash="dot"))

    fig.update_layout(
        **_base_layout(
            title="CoP Spatial Density (2D Histogram Contour)",
            xaxis=dict(title="Mediolateral (cm)", zeroline=False, gridcolor="#eee"),
            yaxis=dict(
                title="Anteroposterior (cm)",
                zeroline=False,
                gridcolor="#eee",
                scaleanchor="x",
                scaleratio=1,
            ),
        )
    )
    return fig


# ---------------------------------------------------------------------------
# 7. Full Feature Summary Table
# ---------------------------------------------------------------------------

# Each entry is either:
#   ("header", section_title)                  — coloured section divider row
#   ("data", key, label, unit, fmt)            — data row
# fmt=None → display as raw string   fmt="d" → integer
_TABLE_SECTIONS: list = [
    ("header", "Session Info"),
    ("data", "source_file", "Source file", "", None),
    ("data", "duration_s", "Recording duration", "s", ".1f"),
    ("data", "total_weight_kg", "Body weight", "kg", ".1f"),
    ("data", "n_samples_raw", "Raw samples", "", "d"),
    ("data", "ui_filter_window", "Display filter window", "frames", "d"),
    ("header", "Positional"),
    ("data", "mean_value_ML", "Mean position — ML", "cm", ".3f"),
    ("data", "mean_value_AP", "Mean position — AP", "cm", ".3f"),
    ("data", "mean_distance_ML", "Mean displacement — ML", "cm", ".3f"),
    ("data", "mean_distance_AP", "Mean displacement — AP", "cm", ".3f"),
    ("data", "mean_distance_Radius", "Mean displacement — Radius", "cm", ".3f"),
    ("data", "maximal_distance_ML", "Max displacement — ML", "cm", ".3f"),
    ("data", "maximal_distance_AP", "Max displacement — AP", "cm", ".3f"),
    ("data", "maximal_distance_Radius", "Max displacement — Radius", "cm", ".3f"),
    ("data", "rms_ML", "RMS — ML", "cm", ".3f"),
    ("data", "rms_AP", "RMS — AP", "cm", ".3f"),
    ("data", "rms_Radius", "RMS — Radius", "cm", ".3f"),
    ("data", "range_ML", "Range — ML", "cm", ".3f"),
    ("data", "range_AP", "Range — AP", "cm", ".3f"),
    ("data", "range_ML_AND_AP", "Range — ML+AP", "cm", ".3f"),
    ("data", "range_ratio_ML_AND_AP", "Range ratio ML/AP", "", ".3f"),
    ("data", "planar_deviation_ML_AND_AP", "Planar deviation", "cm", ".3f"),
    ("data", "coefficient_sway_direction_ML_AND_AP", "Sway direction coefficient", "", ".5f"),
    ("data", "confidence_ellipse_area_ML_AND_AP", "95% confidence ellipse area", "cm²", ".3f"),
    ("data", "principal_sway_direction_ML_AND_AP", "Principal sway direction", "°", ".2f"),
    ("header", "Dynamic"),
    ("data", "mean_velocity_ML", "Mean velocity — ML", "cm/s", ".3f"),
    ("data", "mean_velocity_AP", "Mean velocity — AP", "cm/s", ".3f"),
    ("data", "mean_velocity_ML_AND_AP", "Mean velocity — ML+AP", "cm/s", ".3f"),
    ("data", "sway_area_per_second_ML_AND_AP", "Sway area per second", "cm²/s", ".4f"),
    ("data", "phase_plane_parameter_ML", "Phase plane parameter — ML", "", ".4f"),
    ("data", "phase_plane_parameter_AP", "Phase plane parameter — AP", "", ".4f"),
    ("data", "LFS_ML_AND_AP", "Long-range fractal scaling", "", ".4f"),
    ("data", "fractal_dimension_ML_AND_AP", "Fractal dimension", "", ".4f"),
    ("header", "Sway Density (SPD)"),
    ("data", "zero_crossing_SPD_ML", "Zero crossings — ML", "", "d"),
    ("data", "peak_velocity_pos_SPD_ML", "Peak velocity (positive) — ML", "cm/s", ".4f"),
    ("data", "peak_velocity_neg_SPD_ML", "Peak velocity (negative) — ML", "cm/s", ".4f"),
    ("data", "peak_velocity_all_SPD_ML", "Peak velocity (mean) — ML", "cm/s", ".4f"),
    ("data", "zero_crossing_SPD_AP", "Zero crossings — AP", "", "d"),
    ("data", "peak_velocity_pos_SPD_AP", "Peak velocity (positive) — AP", "cm/s", ".4f"),
    ("data", "peak_velocity_neg_SPD_AP", "Peak velocity (negative) — AP", "cm/s", ".4f"),
    ("data", "peak_velocity_all_SPD_AP", "Peak velocity (mean) — AP", "cm/s", ".4f"),
    ("data", "mean_peak_Sway_Density", "Mean peak sway density", "s", ".4f"),
    ("data", "mean_distance_peak_Sway_Density", "Mean distance between SD peaks", "cm", ".4f"),
    ("header", "Frequency (Power Spectral Density)"),
    ("data", "mean_frequency_ML", "Mean frequency — ML", "Hz", ".4f"),
    ("data", "mean_frequency_AP", "Mean frequency — AP", "Hz", ".4f"),
    ("data", "mean_frequency_ML_AND_AP", "Mean frequency — ML+AP", "Hz", ".4f"),
    ("data", "total_power_Power_Spectrum_Density_ML", "Total PSD power — ML", "cm²/Hz", ".4f"),
    ("data", "total_power_Power_Spectrum_Density_AP", "Total PSD power — AP", "cm²/Hz", ".4f"),
    (
        "data",
        "power_frequency_50_Power_Spectrum_Density_ML",
        "50% power frequency — ML",
        "Hz",
        ".4f",
    ),
    (
        "data",
        "power_frequency_50_Power_Spectrum_Density_AP",
        "50% power frequency — AP",
        "Hz",
        ".4f",
    ),
    (
        "data",
        "power_frequency_95_Power_Spectrum_Density_ML",
        "95% power frequency — ML",
        "Hz",
        ".4f",
    ),
    (
        "data",
        "power_frequency_95_Power_Spectrum_Density_AP",
        "95% power frequency — AP",
        "Hz",
        ".4f",
    ),
    ("data", "frequency_mode_Power_Spectrum_Density_ML", "Frequency mode — ML", "Hz", ".4f"),
    ("data", "frequency_mode_Power_Spectrum_Density_AP", "Frequency mode — AP", "Hz", ".4f"),
    (
        "data",
        "centroid_frequency_Power_Spectrum_Density_ML",
        "Centroid frequency — ML",
        "Hz",
        ".4f",
    ),
    (
        "data",
        "centroid_frequency_Power_Spectrum_Density_AP",
        "Centroid frequency — AP",
        "Hz",
        ".4f",
    ),
    (
        "data",
        "frequency_dispersion_Power_Spectrum_Density_ML",
        "Frequency dispersion — ML",
        "",
        ".4f",
    ),
    (
        "data",
        "frequency_dispersion_Power_Spectrum_Density_AP",
        "Frequency dispersion — AP",
        "",
        ".4f",
    ),
    (
        "data",
        "energy_content_below_05_Power_Spectrum_Density_ML",
        "Energy < 0.5 Hz — ML",
        "cm²",
        ".4f",
    ),
    (
        "data",
        "energy_content_below_05_Power_Spectrum_Density_AP",
        "Energy < 0.5 Hz — AP",
        "cm²",
        ".4f",
    ),
    ("data", "energy_content_05_2_Power_Spectrum_Density_ML", "Energy 0.5–2 Hz — ML", "cm²", ".5f"),
    ("data", "energy_content_05_2_Power_Spectrum_Density_AP", "Energy 0.5–2 Hz — AP", "cm²", ".5f"),
    (
        "data",
        "energy_content_above_2_Power_Spectrum_Density_ML",
        "Energy > 2 Hz — ML",
        "cm²",
        ".6f",
    ),
    (
        "data",
        "energy_content_above_2_Power_Spectrum_Density_AP",
        "Energy > 2 Hz — AP",
        "cm²",
        ".6f",
    ),
    ("data", "frequency_quotient_Power_Spectrum_Density_ML", "Frequency quotient — ML", "", ".6f"),
    ("data", "frequency_quotient_Power_Spectrum_Density_AP", "Frequency quotient — AP", "", ".6f"),
    ("header", "Diffusion / SDA — Mediolateral"),
    (
        "data",
        "short_time_diffusion_Diffusion_ML",
        "Short-time diffusion coeff — ML",
        "cm²/s",
        ".4f",
    ),
    ("data", "long_time_diffusion_Diffusion_ML", "Long-time diffusion coeff — ML", "cm²/s", ".4f"),
    ("data", "critical_time_Diffusion_ML", "Critical time (t*) — ML", "s", ".3f"),
    ("data", "critical_displacement_Diffusion_ML", "Critical displacement — ML", "cm²", ".4f"),
    ("data", "short_time_scaling_Diffusion_ML", "Short-time Hurst exponent — ML", "", ".4f"),
    ("data", "long_time_scaling_Diffusion_ML", "Long-time Hurst exponent — ML", "", ".4f"),
    ("header", "Diffusion / SDA — Anteroposterior"),
    (
        "data",
        "short_time_diffusion_Diffusion_AP",
        "Short-time diffusion coeff — AP",
        "cm²/s",
        ".4f",
    ),
    ("data", "long_time_diffusion_Diffusion_AP", "Long-time diffusion coeff — AP", "cm²/s", ".4f"),
    ("data", "critical_time_Diffusion_AP", "Critical time (t*) — AP", "s", ".3f"),
    ("data", "critical_displacement_Diffusion_AP", "Critical displacement — AP", "cm²", ".4f"),
    ("data", "short_time_scaling_Diffusion_AP", "Short-time Hurst exponent — AP", "", ".4f"),
    ("data", "long_time_scaling_Diffusion_AP", "Long-time Hurst exponent — AP", "", ".4f"),
]

_SECTION_FILL = "#dce6f5"
_SECTION_FONT = "#2a4a80"
_ROW_FILLS = ["#f7f9fc", "white"]


def build_feature_table(features: dict) -> go.Figure:
    labels_col: list = []
    values_col: list = []
    fill_labels: list = []
    fill_values: list = []
    font_labels: list = []
    font_values: list = []
    data_row_idx = 0

    for entry in _TABLE_SECTIONS:
        if entry[0] == "header":
            labels_col.append(f"<b>{entry[1]}</b>")
            values_col.append("")
            for col_fill, col_font in [(fill_labels, font_labels), (fill_values, font_values)]:
                col_fill.append(_SECTION_FILL)
                col_font.append(_SECTION_FONT)
        else:
            _, key, label, unit, fmt = entry
            val = features.get(key)
            if val is None:
                continue
            if fmt is None:
                formatted = str(val)
            elif fmt == "d":
                formatted = str(int(val))
            else:
                formatted = f"{val:{fmt}}"
            display_val = f"{formatted} {unit}".strip() if unit else formatted
            labels_col.append(label)
            values_col.append(display_val)
            row_color = _ROW_FILLS[data_row_idx % 2]
            fill_labels.append(row_color)
            fill_values.append(row_color)
            font_labels.append("#333")
            font_values.append("#333")
            data_row_idx += 1

    fig = go.Figure(
        data=[
            go.Table(
                header=dict(
                    values=["<b>Feature</b>", "<b>Value</b>"],
                    fill_color="#4C72B0",
                    font=dict(color="white", size=13),
                    align="left",
                    height=32,
                ),
                cells=dict(
                    values=[labels_col, values_col],
                    fill_color=[fill_labels, fill_values],
                    align="left",
                    font=dict(size=12, color=[font_labels, font_values]),
                    height=26,
                ),
            )
        ]
    )
    n_rows = len(labels_col)
    fig.update_layout(
        **_base_layout(
            title="Full Feature Summary",
            height=max(400, 32 + n_rows * 26 + 50),
            margin=dict(l=20, r=20, t=50, b=20),
        )
    )
    return fig


# ---------------------------------------------------------------------------
# HTML template
# ---------------------------------------------------------------------------

_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>WIIBBLE Posturographic Report — {{ session_date }}</title>
  <style>
    /* ── Base ── */
    *, *::before, *::after { box-sizing: border-box; }
    body {
      font-family: Arial, sans-serif;
      font-size: 14px;
      color: #333;
      background: #f4f6f9;
      margin: 0;
      padding: 0 16px 40px;
    }

    /* ── Header ── */
    .report-header {
      background: #4C72B0;
      color: white;
      padding: 24px 32px;
      margin: 0 -16px 32px;
    }
    .report-header h1 { margin: 0 0 6px; font-size: 22px; }
    .report-header .meta { font-size: 13px; opacity: 0.88; }
    .report-header .meta span { margin-right: 24px; }

    /* ── Section cards ── */
    .section {
      background: white;
      border-radius: 8px;
      box-shadow: 0 1px 4px rgba(0,0,0,0.08);
      padding: 20px 24px 16px;
      margin-bottom: 24px;
    }
    .section h2 {
      margin: 0 0 4px;
      font-size: 16px;
      color: #4C72B0;
      border-bottom: 2px solid #e8ecf4;
      padding-bottom: 8px;
    }
    .interpretation {
      background: #f0f4fb;
      border-left: 4px solid #4C72B0;
      padding: 10px 14px;
      margin: 12px 0 0;
      font-size: 13px;
      color: #444;
      border-radius: 0 4px 4px 0;
    }
    .interpretation strong { color: #4C72B0; }

    /* ── Two-column grid (wide screens only) ── */
    .grid-2 {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 24px;
    }
    @media (max-width: 900px) {
      .grid-2 { grid-template-columns: 1fr; }
    }

    /* ── Footer ── */
    footer {
      margin-top: 40px;
      padding: 16px 0 0;
      border-top: 1px solid #ddd;
      font-size: 11px;
      color: #888;
    }
    footer h3 { font-size: 12px; color: #666; margin: 0 0 6px; }
    footer p  { margin: 4px 0; }

    /* ── Print ── */
    @media print {
      body { background: white; padding: 0; }
      .report-header { margin: 0 0 20px; }
      .section { box-shadow: none; border: 1px solid #ddd; page-break-inside: avoid; }
      .grid-2 { grid-template-columns: 1fr 1fr; }
    }
  </style>
</head>
<body>

<div class="report-header">
  <h1>WIIBBLE Posturographic Report</h1>
  <div class="meta">
    <span>📅 {{ session_date }}</span>
    <span>⚖️ Body weight: {{ weight_kg }} kg</span>
    <span>⏱ Duration: {{ duration_s }} s</span>
    <span>📄 Source: {{ source_file }}</span>
    <span>🕐 Generated: {{ generated_at }}</span>
  </div>
</div>

<!-- ══ Row 1: Sway Path + Time Series ══ -->
<div class="grid-2">

  <div class="section">
    <h2>1 · CoP Sway Path &amp; 95% Confidence Ellipse</h2>
    {{ fig_sway_path }}
    <div class="interpretation">
      <strong>Caption:</strong> This plot shows the center of pressure (CoP) trajectory during the recording session as a continuous line. The dashed ellipse indicates the region containing 95% of the observed sway positions.
    </div>
  </div>

  <div class="section">
    <h2>2 · ML / AP Time Series</h2>
    {{ fig_time_series }}
    <div class="interpretation">
      <strong>Caption:</strong> The top and bottom panels display the center of pressure (CoP) position as a function of time, split into mediolateral (ML, blue) and anteroposterior (AP, orange) components.
    </div>
  </div>

</div>

<!-- ══ Row 2: Velocity + PSD ══ -->
<div class="grid-2">

  <div class="section">
    <h2>3 · CoP Velocity Time Series</h2>
    {{ fig_velocity }}
    <div class="interpretation">
      <strong>Caption:</strong> These plots show the instantaneous velocity of the center of pressure (CoP) in the mediolateral (ML) and anteroposterior (AP) directions as a function of time.
    </div>
  </div>

  <div class="section">
    <h2>4 · Power Spectral Density</h2>
    {{ fig_psd }}
    <div class="interpretation">
      <strong>Caption:</strong> This plot depicts the power spectral density (PSD) of the center of pressure (CoP) displacement in mediolateral (ML) and anteroposterior (AP) directions. Shaded regions indicate reference frequency bands, and vertical dashed lines mark selected frequency points.
    </div>
  </div>

</div>

<!-- ══ Row 3: Diffusion + Density ══ -->
<div class="grid-2">

  <div class="section">
    <h2>5 · Diffusion Plot (log-log MSD)</h2>
    {{ fig_diffusion }}
    <div class="interpretation">
      <strong>Caption:</strong> Mean square displacement (MSD) is shown as a function of time interval (Δt) on log–log axes for both mediolateral (ML) and anteroposterior (AP) directions. Dashed lines indicate estimated critical time points.
    </div>
  </div>

  <div class="section">
    <h2>6 · CoP Spatial Density</h2>
    {{ fig_density }}
    <div class="interpretation">
      <strong>Caption:</strong> Contour lines represent regions where the center of pressure (CoP) spent the most time during the test, overlaid on the overall CoP path. Densest regions correspond to more frequent CoP positions.
    </div>
  </div>

</div>

{% if fig_table %}
<!-- ══ Row 4: Full Feature Table ══ -->
<div class="section">
  <h2>7 · Full Feature Summary</h2>
  {{ fig_table }}
  <div class="interpretation">
    <strong>Reference context:</strong> All values are computed from the 25 Hz
    Butterworth-filtered CoP signal. Ellipse area, RMS, and mean velocity are the
    features with the highest test–retest reliability on the Wii Balance Board
    (Leach et al. 2014). Frequency-domain and diffusion features require recordings
    of at least 30 s for stable estimates — interpret with caution for shorter sessions.
    Blue section headers group related features by analysis domain.
  </div>
</div>
{% endif %}

<footer>
  <h3>Methodology</h3>
  <p>CoP computed from Wii Balance Board corner forces using the lever-arm formula
     (Leach et al., 2014, <em>Sensors</em> 14:18244).
     Resampled to 25 Hz via SWARII; low-pass filtered at 10 Hz (4th-order Butterworth, zero-phase).
     Features extracted by <em>code_descriptors_postural_control</em>.</p>
  <p><strong>Key references:</strong>
     Prieto et al. (1996) <em>IEEE Trans Biomed Eng</em> 43:956 ·
     Collins &amp; De Luca (1993) <em>Exp Brain Res</em> 95:308 ·
     Collins et al. (1995) <em>Chaos</em> 5:57 ·
     Rocchi et al. (2002) <em>Med Biol Eng Comput</em> 40:632 ·
     Baratto et al. (2002) <em>Motor Control</em> 6:246</p>
  <p style="margin-top:8px">This report was generated automatically by WIIBBLE and is intended
     to support — not replace — clinical judgement.</p>
</footer>

</body>
</html>
"""


# ---------------------------------------------------------------------------
# Report builder
# ---------------------------------------------------------------------------


def _find_features_json(csv_path: str) -> str | None:
    """Locate the features JSON that matches the CSV timestamp, if it exists."""
    basename = os.path.basename(csv_path)
    # Extract YYYYMMDD_HHMMSS from recording_YYYYMMDD_HHMMSS.csv
    m = re.search(r"(\d{8}_\d{6})", basename)
    if not m:
        return None
    timestamp = m.group(1)
    candidate = os.path.join(os.path.dirname(csv_path), f"features_{timestamp}.json")
    return candidate if os.path.isfile(candidate) else None


def generate_report(
    csv_path: str, features_path: str | None = None, out_path: str | None = None
) -> str:
    """Build the HTML report and write it to disk.

    Parameters
    ----------
    csv_path : str
        Path to a WIIBBLE recording CSV.
    features_path : str, optional
        Path to the corresponding features JSON.  Auto-detected if omitted.
    out_path : str, optional
        Destination HTML file path.  Defaults to ``recordings/report_<timestamp>.html``.

    Returns
    -------
    str
        Absolute path of the written HTML file.
    """
    csv_path = os.path.abspath(csv_path)
    if not os.path.isfile(csv_path):
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    # ── Features JSON ────────────────────────────────────────────────────────
    if features_path is None:
        features_path = _find_features_json(csv_path)
        if features_path:
            log.info("Auto-detected features JSON: %s", features_path)
        else:
            log.warning(
                "No matching features JSON found for '%s'. Feature table will be omitted.",
                os.path.basename(csv_path),
            )

    features: dict | None = None
    if features_path and os.path.isfile(features_path):
        with open(features_path) as f:
            features = json.load(f)

    log.info(f"Loading recording CSV: {csv_path}")
    data, metadata = load_recording(csv_path)
    weight_kg = float((features or metadata).get("total_weight_kg", 0))
    if weight_kg <= 0:
        raise ValueError("Cannot determine total_weight_kg — pass it explicitly or re-record.")

    log.info("Generating Stabilogram and computing CoP series…")
    cop = to_cop_array(data, weight_kg)
    stab = Stabilogram()
    stab.from_array(cop)
    log.info("Signal processing complete.")

    # ── Session metadata for header ──────────────────────────────────────────
    m = re.search(r"(\d{8}_\d{6})", os.path.basename(csv_path))
    if m:
        raw_ts = m.group(1)
        session_date = datetime.datetime.strptime(raw_ts, "%Y%m%d_%H%M%S").strftime(
            "%d %b %Y %H:%M"
        )
    else:
        session_date = "Unknown"

    duration_s = features.get("duration_s") if features else float(data[-1, 0] - data[0, 0])

    log.info("Creating all report figures (Plotly)…")
    t_fig_start = time.time()
    figures = [
        ("fig_sway_path", plot_sway_path(stab, features)),
        ("fig_time_series", plot_time_series(stab)),
        ("fig_velocity", plot_velocity(stab)),
        ("fig_psd", plot_psd(stab, features)),
        ("fig_diffusion", plot_diffusion(stab, features)),
        ("fig_density", plot_density_heatmap(stab)),
    ]
    if features:
        figures.append(("fig_table", build_feature_table(features)))
    t_fig_end = time.time()
    log.info(f"Figures created in {t_fig_end - t_fig_start:.2f}s.")

    # ── Serialise to HTML divs (JS bundle only in first figure) ──────────────
    div_map: dict[str, str] = {}
    first = True
    for name, fig in figures:
        div_map[name] = _fig_html(fig, first=first)
        first = False

    # ── Render template ──────────────────────────────────────────────────────
    tmpl = Template(_HTML_TEMPLATE)
    html = tmpl.render(
        session_date=session_date,
        weight_kg=f"{weight_kg:.1f}",
        duration_s=f"{duration_s:.1f}",
        source_file=os.path.basename(csv_path),
        generated_at=datetime.datetime.now().strftime("%d %b %Y %H:%M"),
        fig_table=div_map.get("fig_table"),
        **{k: v for k, v in div_map.items() if k != "fig_table"},
    )

    # ── Write output ─────────────────────────────────────────────────────────
    log.info("Writing HTML report to disk…")
    if out_path is None:
        # Extract timestamp from CSV filename (recording_YYYYMMDD_HHMMSS.csv)
        m = re.search(r"(\d{8}_\d{6})", os.path.basename(csv_path))
        if m:
            ts = m.group(1)
            out_path = os.path.join(os.path.dirname(csv_path), f"report_{ts}.html")
        else:
            # Fallback: use datetime now if the format is not as expected
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            out_path = os.path.join(os.path.dirname(csv_path), f"report_{ts}.html")
    out_path = os.path.abspath(out_path)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    elapsed = time.time() - start_all
    log.info(f"Report written to {out_path} in {elapsed:.2f} seconds.")
    log.info("Report written to %s (%.2f s total)", out_path, elapsed)
    return out_path


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Generate a posturographic HTML report from a WIIBBLE recording.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python report.py recordings/recording_20260420_130030.csv\n"
            "  python report.py recordings/recording_20260420_130030.csv \\\n"
            "      --features recordings/features_20260420_130030.json \\\n"
            "      --out reports/session1.html"
        ),
    )
    p.add_argument("csv", help="Path to the WIIBBLE recording CSV file.")
    p.add_argument(
        "--features",
        metavar="JSON",
        default=None,
        help="Path to the features JSON file (auto-detected if omitted).",
    )
    p.add_argument(
        "--out",
        metavar="HTML",
        default=None,
        help="Output HTML file path (default: recordings/report_<timestamp>.html).",
    )
    p.add_argument("--verbose", "-v", action="store_true", help="Enable DEBUG logging.")
    return p


if __name__ == "__main__":
    args = _build_parser().parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )
    try:
        output = generate_report(args.csv, features_path=args.features, out_path=args.out)
        print(f"Report saved to: {output}")
    except Exception as exc:
        log.error("Report generation failed: %s", exc)
        sys.exit(1)
