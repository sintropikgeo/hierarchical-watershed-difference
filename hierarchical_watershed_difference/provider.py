"""
Processing provider.

Copyright (C) 2025 by Henrique Ledo Lopes Pinho, Jessica Bassani de Oliveira,
Yzel Rondon Suarez

This program is free software; you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation; either version 2 of the License, or (at your option) any later
version.
"""

import os

from qgis.core import QgsProcessingProvider
from qgis.PyQt.QtGui import QIcon

from .algorithm import HierarchicalWatershedDifferenceAlgorithm


class HierarchicalWatershedProvider(QgsProcessingProvider):

    def loadAlgorithms(self):  # noqa: N802
        self.addAlgorithm(HierarchicalWatershedDifferenceAlgorithm())

    def id(self):
        return "hierarchicalwatershed"

    def name(self):
        return "Hierarchical Watershed Difference"

    def icon(self):
        return QIcon(os.path.join(os.path.dirname(__file__), "icon.png"))

    def longName(self):  # noqa: N802
        return self.name()
