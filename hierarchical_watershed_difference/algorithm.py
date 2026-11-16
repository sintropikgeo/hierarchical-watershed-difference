"""
**********************************************************************************************************************
    Removal of watershed intersection by hierarchical difference.py                                                  *
    -----------------------------------------------------------------------------------------------------------------*
    Date                 : March 2025                                                                                *
    Copyright            : (C) 2025 by Henrique Ledo Lopes Pinho, Jessica Bassani de Oliveira, Yzel Rondon Suarez    *
    Email                : geaaqua@uems.br                                                                           *
**********************************************************************************************************************
*                                                                                                                    *
*   This program is free software; you can redistribute it and/or modify it under the terms of the GNU General       *
*   Public License as published by the Free Software Foundation; either version 2 of the License, or (at your option)*
*   any later version.                                                                                               *
*                                                                                                                    *
**********************************************************************************************************************

Processing algorithm version of the original script. The processing steps are
the same as the script; the paths and parameters that were edited in the code
are now fields of the algorithm window.
"""

import os

import processing
from qgis.core import (
    Qgis,
    QgsApplication,
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingParameterFile,
    QgsProcessingParameterFolderDestination,
    QgsProcessingParameterNumber,
    QgsProject,
    QgsRasterLayer,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtGui import QIcon

# Compatibility between QGIS 3.34 and newer versions (enums moved in 3.36)
try:
    NUMBER_INTEGER = Qgis.ProcessingNumberParameterType.Integer
except AttributeError:
    NUMBER_INTEGER = QgsProcessingParameterNumber.Integer

try:
    FILE_BEHAVIOR = Qgis.ProcessingFileParameterBehavior.File
except AttributeError:
    FILE_BEHAVIOR = QgsProcessingParameterFile.File

try:
    FLAG_NO_THREADING = Qgis.ProcessingAlgorithmFlag.NoThreading
except AttributeError:
    FLAG_NO_THREADING = QgsProcessingAlgorithm.FlagNoThreading


def grass_id(name):
    """GRASS algorithm id: 'grass7:' in QGIS 3.34, 'grass:' in newer versions."""
    registry = QgsApplication.processingRegistry()
    for prefix in ("grass7", "grass"):
        if registry.algorithmById(f"{prefix}:{name}") is not None:
            return f"{prefix}:{name}"
    raise QgsProcessingException(
        f"GRASS algorithm '{name}' not found. Enable the GRASS GIS provider.")


class HierarchicalWatershedDifferenceAlgorithm(QgsProcessingAlgorithm):

    DEM = "DEM"
    EXUTORY_TXT = "EXUTORY_TXT"
    COLLECTION_SHP = "COLLECTION_SHP"
    STREAM_SEGMENTS = "STREAM_SEGMENTS"
    THRESHOLD = "THRESHOLD"
    CONVERGENCE = "CONVERGENCE"
    MEMORY = "MEMORY"
    INTERMEDIARY_DIR = "INTERMEDIARY_DIR"
    FINAL_DIR = "FINAL_DIR"

    def tr(self, text):
        return QCoreApplication.translate("HierarchicalWatershedDifference", text)

    def createInstance(self):  # noqa: N802
        return HierarchicalWatershedDifferenceAlgorithm()

    def name(self):
        return "hierarchicalwatersheddifference"

    def displayName(self):  # noqa: N802
        return self.tr("Removal of watershed intersection by hierarchical difference")

    def group(self):
        return self.tr("Hydrology")

    def groupId(self):  # noqa: N802
        return "hydrology"

    def icon(self):
        return QIcon(os.path.join(os.path.dirname(__file__), "icon.png"))

    def flags(self):
        # Runs in the main thread, like the script in the Python console,
        # so the layers can be added to the project during the processing.
        return super().flags() | FLAG_NO_THREADING

    def shortHelpString(self):  # noqa: N802
        return self.tr(
            "Runs the Difference tool iteratively between intersecting "
            "watershed polygons, giving priority to those with a higher "
            "elevation value. Polygons that encompassed the areas of others "
            "are reduced, so none have overlapping areas.<br><br>"
            "<b>Inputs</b> (all in the same CRS, e.g. UTM)<br>"
            "<i>DEM</i>: pre-processed .tif (mosaic, cropping, correction of "
            "negative values, filling of pixels without data and removal of "
            "spurious depressions).<br>"
            "<i>Exutory coordinates</i>: .txt with the coordinates in x,y "
            "format, separated by a comma, without spaces.<br>"
            "<i>Collected points</i>: .shp with a column called \"Points\" "
            "with the names of the points, in the same order as the "
            "coordinates file.<br>"
            "<i>Stream segments</i> (optional): only loaded into the project "
            "to check that the points are on the stream pixels.<br>"
            "<i>Intermediary files folder</i> and <i>Final polygons "
            "folder</i>: use new or empty folders.<br><br>"
            "<b>Outputs</b><br>"
            "Intermediary folder: drainage_direction.tif, basin_[Point], "
            "corrected_basin_[Point].shp, dissolved_basin_[Point].shp, "
            "zonal_basin_[Point].shp.<br>"
            "Final folder: influence_area_[Point].shp (area of influence of "
            "each point).<br><br>"
            "<b>Requirements</b>: GRASS GIS provider enabled."
        )

    def initAlgorithm(self, config=None):  # noqa: N802
        self.addParameter(QgsProcessingParameterFile(
            self.DEM, self.tr("Digital elevation model (DEM, .tif)"),
            behavior=FILE_BEHAVIOR, fileFilter="GeoTIFF (*.tif *.tiff)"))

        self.addParameter(QgsProcessingParameterFile(
            self.EXUTORY_TXT, self.tr("Exutory coordinates (.txt, x,y)"),
            behavior=FILE_BEHAVIOR, fileFilter="Text files (*.txt)"))

        self.addParameter(QgsProcessingParameterFile(
            self.COLLECTION_SHP,
            self.tr("Collected points (.shp with the \"Points\" column)"),
            behavior=FILE_BEHAVIOR, fileFilter="Shapefile (*.shp)"))

        self.addParameter(QgsProcessingParameterFile(
            self.STREAM_SEGMENTS, self.tr("Stream segments (.tif)"),
            behavior=FILE_BEHAVIOR, fileFilter="GeoTIFF (*.tif *.tiff)",
            optional=True))

        self.addParameter(QgsProcessingParameterNumber(
            self.THRESHOLD,
            self.tr("Threshold for basins outside the main watercourse"),
            NUMBER_INTEGER, 1000, False, 1))

        self.addParameter(QgsProcessingParameterNumber(
            self.CONVERGENCE,
            self.tr("Convergence factor for multiple flow direction"),
            NUMBER_INTEGER, 5, False, 1, 10))

        self.addParameter(QgsProcessingParameterNumber(
            self.MEMORY, self.tr("Maximum memory to be used (MB)"),
            NUMBER_INTEGER, 300, False, 1))

        self.addParameter(QgsProcessingParameterFolderDestination(
            self.INTERMEDIARY_DIR, self.tr("Intermediary files folder")))

        self.addParameter(QgsProcessingParameterFolderDestination(
            self.FINAL_DIR, self.tr("Final polygons folder")))

    # ------------------------------------------------------------------
    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        self.feedback = feedback
        self.dem_path = self.parameterAsFile(parameters, self.DEM, context)
        self.exutory_txt = self.parameterAsFile(parameters, self.EXUTORY_TXT, context)
        self.collection_shp = self.parameterAsFile(parameters, self.COLLECTION_SHP, context)
        self.stream_segments_path = self.parameterAsFile(
            parameters, self.STREAM_SEGMENTS, context)
        self.intermediary_layers_dir = self.parameterAsString(
            parameters, self.INTERMEDIARY_DIR, context)
        self.final_polygon_dir = self.parameterAsString(parameters, self.FINAL_DIR, context)
        self.threshold = self.parameterAsInt(parameters, self.THRESHOLD, context)
        self.convergence = self.parameterAsInt(parameters, self.CONVERGENCE, context)
        self.memory = self.parameterAsInt(parameters, self.MEMORY, context)

        self.process_basin_delimitation()
        feedback.setProgress(60)
        self.calculate_zonal_statistics()
        feedback.setProgress(80)
        self.process_basin_difference()
        feedback.setProgress(100)

        self.print("Processing completed successfully! All the parts have been executed.")
        return {self.INTERMEDIARY_DIR: self.intermediary_layers_dir,
                self.FINAL_DIR: self.final_polygon_dir}

    def print(self, message):
        self.feedback.pushInfo(message)

    # Function to add layers to the project
    # ========================================
    def add_layer_to_project(self, layer, name):
        """
        Adds layers to the QGIS project.
        Checks if the layer is valid and, if so, adds it to the project.
        """
        if layer.isValid():
            QgsProject.instance().addMapLayer(layer)
            self.print(f"Layer '{name}' loaded into the project.")
        else:
            self.print(f"Error: Layer '{name}' is not valid and has not been loaded.")

    # Part 1: River Basin Delimitation
    # ============================================
    def process_basin_delimitation(self):
        """
         Part 1: River Basin Delimitation in QGIS.
        Performs the basin delimitation process using the digital elevation model (DEM)
        and the specified outflow points.
        """
        self.print("Executing Part 1: Basin Delimitation")
        dem_path = self.dem_path
        intermediary_layers_dir = self.intermediary_layers_dir

        # Create the output directories if they don't exist
        os.makedirs(intermediary_layers_dir, exist_ok=True)
        os.makedirs(self.final_polygon_dir, exist_ok=True)

        # Reading the coordinates from the exits file
        outlet_coords = []
        with open(self.exutory_txt, mode='r') as txtfile:
            for line in txtfile:
                # Ignore header and edit coordinates (x, y)
                if 'x' in line.lower() and 'y' in line.lower():
                    continue
                x, y = map(float, line.strip().split(','))
                outlet_coords.append({'x': x, 'y': y})

        # Load the Digital Elevation Model (DEM)
        self.print("Loading the Digital Elevation Model (DEM)...")
        dem_layer = QgsRasterLayer(dem_path, "Digital Elevation Model")
        if not dem_layer.isValid():
            raise QgsProcessingException(f"Erro: The raster could not be loaded in the path {dem_path}")
        self.add_layer_to_project(dem_layer, "Digital Elevation Model")

        # Load the collection points
        self.print("Loading collection points...")
        collection_layer = QgsVectorLayer(self.collection_shp, "Collected Points", "ogr")
        if not collection_layer.isValid():
            raise QgsProcessingException(f"Error: Unable to load point shapefile on path {self.collection_shp}")
        self.add_layer_to_project(collection_layer, "Collected Points")

        # Extract the names of the points collected
        collection_features = collection_layer.getFeatures()
        collection_names = [feature['Points'] for feature in collection_features]

        # If the path of the flow segment has been entered, load the layer
        if self.stream_segments_path:
            self.print("Loading stream segments...")
            segments_layer = QgsRasterLayer(self.stream_segments_path, "Stream Segments")
            if segments_layer.isValid():
                self.add_layer_to_project(segments_layer, "Stream Segments")
            else:
                self.print(f"Erro: Could not load flow segment in path {self.stream_segments_path}")

        # Run r.watershed to calculate drainage direction and stream segments
        self.print("Executing r.watershed...")
        drainage_output = os.path.join(intermediary_layers_dir, "drainage_direction.tif")
        processing.run(grass_id("r.watershed"), {
            'elevation': dem_path,
            'threshold': self.threshold,
            'convergence': self.convergence,
            'memory': self.memory,
            'drainage': drainage_output,
            'GRASS_REGION_PARAMETER': f"{dem_path}",
            'GRASS_REGION_CELLSIZE_PARAMETER': 0
        }, feedback=self.feedback)

        # Load the drainage direction into the project
        drainage_layer = QgsRasterLayer(drainage_output, "Drainage Direction")
        if drainage_layer.isValid():
            self.add_layer_to_project(drainage_layer, "Drainage Direction")
        else:
            self.print(f"Error: Unable to load drainage direction raster in {drainage_output}")

        # Generate watersheds for each exutory of points
        corrected_outputs = []
        for coord, collection_name in zip(outlet_coords, collection_names):
            if self.feedback.isCanceled():
                return
            raster_output = os.path.join(intermediary_layers_dir, f"basin_{collection_name}.tif")
            vector_output = os.path.join(intermediary_layers_dir, f"basin_{collection_name}.shp")
            corrected_output = os.path.join(intermediary_layers_dir, f"corrected_basin_{collection_name}.shp")

            # Execute r.water.outlet to delimit the basin of the exutory point
            self.print(f"Running r.water.outlet for the point {collection_name}...")
            processing.run(grass_id("r.water.outlet"), {
                'input': drainage_output,
                'coordinates': f"{coord['x']},{coord['y']}",
                'output': raster_output,
                'GRASS_REGION_PARAMETER': f"{dem_path}",
                'GRASS_REGION_CELLSIZE_PARAMETER': 0
            }, feedback=self.feedback)

            # Convert the output raster to vector (polygonize)
            self.print("Correcting geometry...")
            processing.run("gdal:polygonize", {
                'INPUT': raster_output,
                'FIELD': "DN",
                'OUTPUT': vector_output
            }, feedback=self.feedback)
            processing.run("native:fixgeometries", {
                'INPUT': vector_output,
                'OUTPUT': corrected_output
            }, feedback=self.feedback)
            corrected_outputs.append(corrected_output)

        # Dissolve the geometries of the corrected basins
        dissolved_outputs = []
        for corrected_output, collection_name in zip(corrected_outputs, collection_names):
            dissolved_output = os.path.join(intermediary_layers_dir, f"dissolved_basin_{collection_name}.shp")

            self.print(f"Dissolving geometries for the point {collection_name}...")
            processing.run("native:dissolve", {
                'INPUT': corrected_output,
                'OUTPUT': dissolved_output
            }, feedback=self.feedback)
            dissolved_outputs.append(dissolved_output)

        self.print("Part 1 successfully completed!")

    # Part 2: Calculating Zonal Statistics
    # ========================================
    def calculate_zonal_statistics(self):
        """
        Part 2: Calculating Zonal Statistics.
        Calculates digital elevation model statistics for each basin.
        """
        self.print("Executing Part 2: Zonal Statistics")
        intermediary_layers_dir = self.intermediary_layers_dir

        # Identify shapefiles in the temporary polygon directory
        shapefiles = [
            os.path.join(intermediary_layers_dir, file)
            for file in os.listdir(intermediary_layers_dir)
            if file.startswith("dissolved_basin_") and file.endswith(".shp")
        ]

        if not shapefiles:
            self.print("No shapefile found to process.")
            return

        self.print(f"Shapefiles found: {shapefiles}")

        # Load the Collected Points layer
        points_layer = QgsVectorLayer(self.collection_shp, "Collected Points", "ogr")
        if not points_layer.isValid():
            self.print("Erro: The file could not be uploaded Collected_Points.shp.")
            return

        points_nomes = [feature["Points"] for feature in points_layer.getFeatures()]
        if len(points_nomes) != len(shapefiles):
            self.print("Error: The number of collected points does not match the number of shapefiles.")
            return

        for shapefile in shapefiles:
            # Extract the shapefile suffix
            suffix = os.path.basename(shapefile).split("dissolved_basin_")[1].replace(".shp", "")

            output_path = os.path.join(intermediary_layers_dir, f"zonal_basin_{suffix}.shp")
            self.print(f"Processing {shapefile} for the suffix {suffix}...")

            # Calculating zonal statistics
            self.print("Calculating zonal statistics...")
            try:
                processing.run("native:zonalstatisticsfb", {
                    'INPUT': shapefile,             # The shapefile containing the basins for which the zonal statistics will be calculated.
                    'INPUT_RASTER': self.dem_path,  # The input raster (in this case, the Digital Elevation Model - DEM).
                    'RASTER_BAND': 1,               # The number of the raster band that will be used for the calculation.
                    'COLUMN_PREFIX': '_',           # Prefix added to the names of the output columns.
                    'STATISTICS': [5],              # 5 = minimum value of the elevations within each polygon.
                    'OUTPUT': output_path           # Path where the output shapefile will be saved.
                }, feedback=self.feedback)
                self.print(f"Zonal statistics calculated for {shapefile}. Output: {output_path}")
            except Exception as e:
                self.print(f"Error in calculating zonal statistics for {shapefile}: {e}")

        self.print("Part 2 successfully completed!")

    # Part 3: Processing Differences between Basins.
    # ==================================================
    def process_basin_difference(self):
        """
        Part 3: Processing differences between basins.
        Sorts shapefiles based on minimum elevation, calculates differences between basins
        to generate unique basins.
        """
        self.print("Executing Part 3: Differences between Basins")
        intermediary_layers_dir = self.intermediary_layers_dir
        final_polygon_dir = self.final_polygon_dir

        shapefiles = [
            os.path.join(intermediary_layers_dir, file)
            for file in os.listdir(intermediary_layers_dir)
            if file.startswith("zonal_basin_") and file.endswith(".shp")
        ]

        if not shapefiles:
            self.print("No zonal basin shapefile found to process.")
            return

        elevation_stats = []
        for shapefile in shapefiles:
            suffix = os.path.basename(shapefile).split("zonal_basin_")[1].replace(".shp", "")

            layer = QgsVectorLayer(shapefile, "", "ogr")
            for feature in layer.getFeatures():
                if '_min' in feature.fields().names():
                    elevation_stats.append({'path': shapefile, 'min': feature['_min'], 'suffix': suffix})

        elevation_stats = sorted(elevation_stats, key=lambda x: x['min'], reverse=True)

        output_files = []

        for i, current_stat in enumerate(elevation_stats):
            suffix = current_stat['suffix']
            # Save influence_area files in the FINAL_POLYGON directory
            output_path = os.path.join(final_polygon_dir, f"influence_area_{suffix}.shp")

            if i == 0:
                processing.run("native:savefeatures", {
                    'INPUT': current_stat['path'],
                    'OUTPUT': output_path
                }, feedback=self.feedback)
            else:
                temp_base_path = current_stat['path']
                for j in range(i):
                    overlay_layer_path = elevation_stats[j]['path']
                    # INTERMEDIARY files remain in INTERMEDIARY LAYERS directory
                    temp_output = os.path.join(intermediary_layers_dir, f"temp_diff_{i}_{j}.shp")
                    processing.run("native:difference", {
                        'INPUT': temp_base_path,
                        'OVERLAY': overlay_layer_path,
                        'OUTPUT': temp_output
                    }, feedback=self.feedback)
                    temp_base_path = temp_output

                processing.run("native:savefeatures", {
                    'INPUT': temp_base_path,
                    'OUTPUT': output_path
                }, feedback=self.feedback)

            output_files.append(output_path)

        # Load final influence_area files from FINAL_POLYGON directory
        project = QgsProject.instance()
        for output_file in output_files:
            layer_name = os.path.basename(output_file).replace(".shp", "")
            layer = QgsVectorLayer(output_file, layer_name, "ogr")
            if layer.isValid():
                project.addMapLayer(layer)

        self.print("Part 3 successfully completed!")
