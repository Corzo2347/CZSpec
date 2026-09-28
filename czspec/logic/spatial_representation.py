"""Perfiles paramétricos y geometría celeste usados por el módulo 6."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import math
from typing import Iterable

import numpy as np


FWHM_TO_SIGMA = 1.0 / (2.0 * math.sqrt(2.0 * math.log(2.0)))


@dataclass
class SpatialLayerSpec:
    layer_id: str
    name: str
    family: str
    profile: str
    center_ra_deg: float
    center_dec_deg: float
    scale_arcsec: float
    ring_radius_arcsec: float = 0.0
    color: str = "#14B8A6"
    line_width: float = 2.0
    levels: list[float] = field(default_factory=lambda: [0.2, 0.4, 0.6, 0.8])
    visible: bool = True
    method: str = ""
    tex_k: float | None = None
    molecule: str = ""
    column_density_cm2: float | None = None
    uncertainty_cm2: float | None = None
    observed_beam_arcsec: float | None = None
    common_beam_arcsec: float | None = None

    def as_dict(self) -> dict:
        return asdict(self)


def centered_profile(radius_arcsec, sigma_arcsec: float):
    radius = np.asarray(radius_arcsec, dtype=float)
    if sigma_arcsec <= 0:
        raise ValueError("La escala espacial debe ser positiva.")
    return np.exp(-0.5 * (radius / sigma_arcsec) ** 2)


def annular_profile(radius_arcsec, ring_radius_arcsec: float, sigma_arcsec: float):
    radius = np.asarray(radius_arcsec, dtype=float)
    if sigma_arcsec <= 0 or ring_radius_arcsec < 0:
        raise ValueError("El radio anular no puede ser negativo y la escala debe ser positiva.")
    return np.exp(-0.5 * ((radius - ring_radius_arcsec) / sigma_arcsec) ** 2)


def convolved_sigma_arcsec(intrinsic_sigma_arcsec: float, beam_fwhm_arcsec: float) -> float:
    if intrinsic_sigma_arcsec < 0 or beam_fwhm_arcsec < 0:
        raise ValueError("La escala y el haz no pueden ser negativos.")
    beam_sigma = beam_fwhm_arcsec * FWHM_TO_SIGMA
    return math.sqrt(intrinsic_sigma_arcsec**2 + beam_sigma**2)


def homogenized_sigma_arcsec(
    intrinsic_sigma_arcsec: float,
    observed_beam_fwhm_arcsec: float,
    target_beam_fwhm_arcsec: float = 29.0,
) -> float:
    """Aplica sólo el núcleo requerido para llegar al haz común solicitado."""

    if min(intrinsic_sigma_arcsec, observed_beam_fwhm_arcsec, target_beam_fwhm_arcsec) < 0:
        raise ValueError("Los tamaños angulares no pueden ser negativos.")
    if observed_beam_fwhm_arcsec >= target_beam_fwhm_arcsec:
        return float(intrinsic_sigma_arcsec)
    kernel_fwhm = math.sqrt(
        target_beam_fwhm_arcsec**2 - observed_beam_fwhm_arcsec**2
    )
    return convolved_sigma_arcsec(intrinsic_sigma_arcsec, kernel_fwhm)


def contour_radii_arcsec(
    profile: str,
    sigma_arcsec: float,
    levels: Iterable[float],
    ring_radius_arcsec: float = 0.0,
) -> list[tuple[float, float]]:
    """Devuelve pares ``(nivel, radio)`` para dibujar isocontornos circulares."""

    if sigma_arcsec <= 0:
        raise ValueError("La escala espacial debe ser positiva.")
    contours: list[tuple[float, float]] = []
    for level in sorted({float(value) for value in levels}):
        if not 0.0 < level < 1.0:
            raise ValueError("Los niveles deben estar estrictamente entre 0 y 1.")
        offset = sigma_arcsec * math.sqrt(-2.0 * math.log(level))
        if profile == "centrado":
            contours.append((level, offset))
        elif profile == "anular":
            inner = ring_radius_arcsec - offset
            if inner > 0:
                contours.append((level, inner))
            contours.append((level, ring_radius_arcsec + offset))
        else:
            raise ValueError(f"Perfil espacial no reconocido: {profile}")
    return contours


def circle_sky_vertices(
    center_ra_deg: float,
    center_dec_deg: float,
    radius_arcsec: float,
    *,
    samples: int = 181,
) -> list[list[float]]:
    """Círculo de pequeño ángulo en coordenadas ICRS para Aladin Lite."""

    if radius_arcsec < 0:
        raise ValueError("El radio no puede ser negativo.")
    if not -90.0 <= center_dec_deg <= 90.0:
        raise ValueError("La declinación debe estar entre -90° y 90°.")
    samples = max(16, int(samples))
    dec_rad = math.radians(center_dec_deg)
    cos_dec = max(abs(math.cos(dec_rad)), 1e-8)
    radius_deg = radius_arcsec / 3600.0
    result = []
    for angle in np.linspace(0.0, 2.0 * math.pi, samples):
        dra = radius_deg * math.cos(angle) / cos_dec
        ddec = radius_deg * math.sin(angle)
        result.append([float((center_ra_deg + dra) % 360.0), float(center_dec_deg + ddec)])
    return result


def layer_contours(layer: SpatialLayerSpec) -> list[dict]:
    contours = []
    for level, radius in contour_radii_arcsec(
        layer.profile,
        layer.scale_arcsec,
        layer.levels,
        layer.ring_radius_arcsec,
    ):
        contours.append(
            {
                "level": level,
                "radius_arcsec": radius,
                "vertices": circle_sky_vertices(
                    layer.center_ra_deg,
                    layer.center_dec_deg,
                    radius,
                ),
            }
        )
    return contours


def aladin_payload(layers: Iterable[SpatialLayerSpec]) -> list[dict]:
    payload = []
    for layer in layers:
        item = layer.as_dict()
        item["contours"] = layer_contours(layer)
        payload.append(item)
    return payload
