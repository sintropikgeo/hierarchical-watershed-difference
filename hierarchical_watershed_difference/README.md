# Removal of watershed intersection by hierarchical difference (QGIS plugin)

Plugin version of the script "Removal of watershed intersection by hierarchical difference". The processing is the same as the script: the paths and parameters that were edited in the code are now fields of the algorithm window.

Runs the Difference tool iteratively between intersecting polygons, giving priority to those with a higher elevation value. Polygons that previously encompassed the areas of others are reduced in size, ensuring that none have overlapping areas. Tools used: r.watershed, r.water.outlet, Polygonize, Fix Geometries, Dissolve, Zonal Statistics and Difference.

## Requirements

- QGIS 3.34.5 or higher (Windows or Linux)
- GRASS GIS provider enabled in Processing

## Usage

`Processing Toolbox > Hierarchical Watershed Difference > Hydrology > Removal of watershed intersection by hierarchical difference`

| Field | Script variable |
|---|---|
| Digital elevation model (DEM, .tif) | `dem_path` |
| Exutory coordinates (.txt, x,y) | `exutory_txt` |
| Collected points (.shp with the "Points" column) | `collection_shp` |
| Stream segments (.tif), optional | `stream_segments_path` |
| Threshold | `threshold` (default 1000) |
| Convergence factor | `convergence` (default 5) |
| Maximum memory (MB) | `memory` (default 300) |
| Intermediary files folder | `intermediary_layers_dir` |
| Final polygons folder | `final_polygon_dir` |

## Necessary files

- All in the same Coordinate Reference System (we use UTM)
- DEM: `.tif`, pre-processed (mosaic, cropping, correction of negative values, filling in pixels without data and removal of spurious depressions)
- Exutory coordinates: `.txt` with coordinates in `x,y` format, on the pixel of the stream segment
- Collected points: `.shp` with a column called "Points" with the names of the points, in the same order as the coordinates file

## Generated outputs

- `drainage_direction.tif`: drainage direction
- `basin_[Point].shp`: delimited basin for each exutory point
- `dissolved_basin_[Point].shp`: basins with corrected geometries
- `zonal_basin_[Point].shp`: zonal statistics (minimum elevation)
- `influence_area_[Point].shp` (final folder): area of influence of each point

## Situations in which the algorithm will not work

- QGIS versions prior to 3.34
- Different coordinate reference system between the .shp file and the raster file
- Exutory coordinates outside the pixel of the stream segment
- Spaces in the .txt file
- Exutory coordinates in a different order from the .shp file
- Column name different from "Points"
- Running a second time using folders that already contain results from a previous run

## Authors

- Henrique Ledo Lopes Pinho
- Jéssica Bassani de Oliveira
- Yzel Rondon Suarez

Contact: geaaqua@uems.br

## Institutional support

State University of Mato Grosso do Sul (UEMS), Dourados, Brazil: CERNA, PGRN, Bachelor's Degree in Information Systems, GEAAQUA and NIT. Funding: CAPES, CNPq and Fundect.

## License

GNU General Public License v2 or later. See `LICENSE`.
