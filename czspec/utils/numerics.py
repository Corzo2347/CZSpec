"""Compatibilidad numérica entre las versiones admitidas de NumPy."""

from __future__ import annotations

from typing import Any

import numpy as np


def trapezoidal_integral(y: Any, x: Any) -> float:
    """Integra dos vectores unidimensionales con la regla trapezoidal.

    ``numpy.trapz`` desapareció en NumPy 2.x y ``numpy.trapezoid`` no existe
    en todas las versiones 1.x admitidas por CZSpec. Esta implementación
    pequeña evita depender de cualquiera de los dos nombres.
    """

    y_values = np.asarray(y, dtype=float)
    x_values = np.asarray(x, dtype=float)
    if y_values.ndim != 1 or x_values.ndim != 1:
        raise ValueError("La integración trapezoidal requiere dos vectores.")
    if y_values.size != x_values.size:
        raise ValueError("Los vectores de integración deben tener la misma longitud.")
    if y_values.size < 2:
        return 0.0
    return float(np.sum(0.5 * (y_values[1:] + y_values[:-1]) * np.diff(x_values)))
