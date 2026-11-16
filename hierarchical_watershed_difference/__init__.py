"""
Hierarchical Watershed Difference - QGIS plugin entry point.

Copyright (C) 2025 by Henrique Ledo Lopes Pinho, Jessica Bassani de Oliveira,
Yzel Rondon Suarez

This program is free software; you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation; either version 2 of the License, or (at your option) any later
version.
"""


def classFactory(iface):  # noqa: N802 (name required by QGIS)
    from .plugin import HierarchicalWatershedDifferencePlugin
    return HierarchicalWatershedDifferencePlugin(iface)
