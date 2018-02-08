"""
ARD related functionality
"""
import os
from functools import partial, lru_cache
from itertools import chain
from typing import Union, NamedTuple, Tuple

from osgeo import gdal
import numpy as np
import merlin


# Typing Jazz
Num = Union[float, int]


class GeoExtent(NamedTuple):
    """
    Simple container to organize projected spatial extent parameters.
    """
    xmin: Num
    ymax: Num
    xmax: Num
    ymin: Num


class GeoCoordinate(NamedTuple):
    """
    Simple container to keep a projected coordinate pair together.
    """
    x: Num
    y: Num


class RowColumn(NamedTuple):
    """
    Simple container to keep a row/column pair together.
    """
    row: int
    column: int


class RowColumnExtent(NamedTuple):
    """
    Simple container to organize row/column extent parameters.
    """
    st_row: int
    st_col: int
    end_row: int
    end_col: int


class ARDattributes(NamedTuple):
    """
    Container for ARD acquisition information derived from the filename.
    """
    sensor: str
    region: str
    h: int
    v: int
    acqdate: int
    procdate: int
    collec: str
    version: str
    contents: str

# Adapting from merlin
# def create(x, y, chipseq, dateseq, locations, spec_index):
#     """Transforms a sequence of chips into a sequence of rods
#        filtered by date, deduplicated, sorted, located and identified.
#        Args:
#            x (int): x projection coordinate of chip
#            y (int): y projection coordinate of chip
#            chipseq (seq): sequence of chips
#            dates (seq): sequence of dates that should be included in the rods
#            locations (numpy.Array): 2d numpy array of pixel coordinates
#            spec_index (dict): specs indexed by ubid
#        Returns:
#            dict: {(chip_x, chip_y, x, y): {'k1': [], 'k2': [], 'k3': [], ...}}
#     """
#
#     return thread_last(chipseq,
#                        partial(chips.trim, dates=dateseq),
#                        chips.deduplicate,
#                        chips.rsort,
#                        partial(chips.to_numpy, spec_index=spec_index),
#                        excepts(ValueError, from_chips, lambda _: []),
#                        excepts(AttributeError, partial(locate, locations=locations), lambda _: {}),
#                        partial(identify, x=x, y=y))


def timeseries(x: Num, y: Num, params: dict):
    coord = GeoCoordinate(x, y)
    h, v = determine_hv(coord, params['region-tileaff'])

    hvroot = os.path.join(params['file-root'], 'h{:02d}v{:02d}'.format(h, v))

    filesdict = {'refl_files': tarfiles(hvroot, params['acquired'], params['region'], params['refl']),
                 'therm_files': tarfiles(hvroot, params['acquired'], params['region'], 'BT')}

    layers = layersdict(filesdict, hvroot, params)

    chips = layerstochips(coord, layers, params)


def layersdict(files: dict, root, params: dict):
    ret = {}
    for layer in params['file-specs']:
        if layer == 'thermals':
            ret[layer] = [vsipath(os.path.join(root, rf), layer, params['file-specs'], params['refl'])
                          for rf in files['therm_files']]
        else:
            ret[layer] = [vsipath(os.path.join(root, rf), layer, params['file-specs'], params['refl'])
                          for rf in files['refl_files']]

    return ret


def layerstochips(coord, layers, params):
    h, v = determine_hv(coord, params['region-tileaff'])
    _, affine = ard_hv(h, v, params['region-extent'])

    ret = {}
    for layer in layers:
        ret[layer] = np.array([extract_chip(path, coord, affine)
                               for path in layers[layer]])

    return ret


@lru_cache(maxsize=3)
def filenameattr(filename: str) -> ARDattributes:
    """
    Provide a centralized function for deriving pertinent information from a given filename.

    Args:
        filename: ARD tarball file name

    Returns:
        namedtuple
    """

    attributes = filename[:-4].split('_')
    h = attributes[2][:3]
    v = attributes[2][-3:]

    return ARDattributes(attributes[0],
                         attributes[1],
                         int(h),
                         int(v),
                         int(attributes[3]),
                         int(attributes[4]),
                         attributes[5],
                         attributes[6],
                         attributes[7])


def vsipath(tarpath: str, band: str, specs: dict, refl: str) -> str:
    """
    Build the GDAL VSI path for the layer of interest inside of a given tarball.

    Args:
        tarpath: path to tarball
        band: spectral band of interest, blue green red etc...
        specs: dict identifying the sensor specific spectral to numeric band combinations
        refl: relates to the type of reflectance values associated with the tarball,
            'SR' 'TA' 'BT' or '' for pixelqa

    Returns:
        string GDAL VSI path
    """
    # Basically a bunch of string manipulations...
    tarfile = os.path.split(tarpath)[-1]
    sensor = filenameattr(tarfile).sensor

    layer = tarfile[:-6] + specs[band][sensor].format(refl=refl)

    path = os.path.join(tarpath, layer)

    return '/vsitar/' + path


@lru_cache(maxsize=72)
def tarfiles(path: str, acquired: str, region: str, tar: str) -> list:
    """
    Provide a listing of all tarballs that meet the requirements for processing.

    Args:
        path: ARD h##v## tile directory
        acquired: ISO8601 date range
        region: region of interest, 'CU' 'AK' or 'HI'
        tar: tarballs of interests, 'SR' 'TA' 'BT' or 'QA'

    Returns:
        list
    """
    fs = filters(acquired, region, tar)

    return [x for x in dirlisting(path) if all(f(x) for f in fs)]


@lru_cache(maxsize=3)
def filters(acquired: str, region: str, tar: str) -> list:
    """
    Sets up the filters when scanning through the ARD data directories.

    Args:
        acquired: ISO8601 date range
        region: region of interest, 'CU' 'AK' or 'HI'
        tar: tarballs of interests, 'SR' 'TA' 'BT' or 'QA'

    Returns:
        list
    """
    return [partial(filter_date, dates=acquired),
            partial(filter_tar, tar=tar),
            partial(filter_reg, region=region)]


@lru_cache(maxsize=9)
def dirlisting(path: str) -> list:
    """
    Helper function around os.listdir for caching.

    Args:
        path: path to pass to os.listdir

    Returns:
        list
    """
    return os.listdir(path)


def filter_date(filename: str, dates: str) -> bool:
    """
    Helper function to filter ARD files based on their acquisition date.

    Args:
        filename: ARD file name
        dates: ISO8601 date range

    Returns:
        bool
    """
    fr, to = dates.replace('-', '').split('/')
    acq = filenameattr(filename).acqdate

    return int(fr) <= acq <= int(to)


def filter_tar(filename: str, tar: str) -> bool:
    """
    Help determine what the particular contents of a ARD tarball is.
    SR -> surface reflectance
    TA -> top of atmosphere
    QA -> quality
    BT -> brightness temperature

    Args:
        filename: ARD file name
        tar: subset of interest

    Returns:
        bool
    """
    return filename.endswith('{}.tar'.format(tar))


def filter_reg(filename: str, region: str) -> bool:
    """
    Determine which region the file is part of.
    CU -> CONUS
    AK -> Alaska
    HI -> Hawaii

    Args:
        filename: ARD file name
        region: region of interest

    Returns:
        bool
    """
    reg = filenameattr(filename).region

    return reg == region


def ard_hv(h: int, v: int, extent: GeoExtent) -> Tuple[GeoExtent, tuple]:
    """
    Geospatial extent and 30m affine for a given ARD grid location.

    Args:
        h (int): horizontal grid number
        v (int): vertical grid number
        extent (sequence): ARD reference extent

    Returns:
        GeoExtent and GeoAffine namedtuples

    Examples:
        >>> ardconus = GeoExtent(xmin=-2565585, ymax=3314805, xmax=2384415, ymin=14805)
        >>> ext, aff = ard_hv(5, 2, ardconus)
        >>> ext
        GeoExtent(xmin=-1815585, ymax=3014805, xmax=-1665585, ymin=2864805)
        >>> aff
        GeoAffine(ulx=-1815585, xres=30, rot1=0, uly=3014805, rot2=0, yres=-30)
    """
    # Spelled out for clarity
    xmin = extent[0] + h * 5000 * 30
    xmax = extent[0] + h * 5000 * 30 + 5000 * 30
    ymax = extent[1] - v * 5000 * 30
    ymin = extent[1] - v * 5000 * 30 - 5000 * 30

    return (GeoExtent(xmin, ymax, xmax, ymin),
            (xmin, 30, 0, ymax, 0, -30))


def fifteen_offset(val: Num) -> int:
    """
    Aligns a given coordinate with nearest value that is a multiple of 15 and
    an odd number. Used for aligning the upper left of a given pixel to the
    USGS standard 30 meter grid.

    Args:
        val: value to adjust

    Returns:
        int

    Examples:
        >>> fifteen_offset(1)
        15
        >>> fifteen_offset(-1)
        -15
        >>> fifteen_offset(0)
        15
        >>> fifteen_offset(0.1)
        15
    """
    return int(val // 30) * 30 + 15


def transform_geo(coord: GeoCoordinate, affine: tuple) -> RowColumn:
    """
    Perform the affine transformation from a geospatial coordinate to row/col
    space.

    This function assumes that you are seeking the row and column of the pixel
    that the spatial coordinate falls in, for a given affine.

    Yline = (Ygeo - GT(3) - Xpixel*GT(4)) / GT(5)
    Xpixel = (Xgeo - GT(0) - Yline*GT(2)) / GT(1)

    From:
    http://www.gdal.org/gdal_datamodel.html

    Args:
        coord (sequence): (x, y) coordinate pair
        affine (sequence): transformation tuple

    Returns:
        RowColumn namedtuple

    Examples:
        >>> ext, aff = ard_hv(5, 2)
        >>> aff
        GeoAffine(ulx=-1815585, xres=30, rot1=0, uly=3014805, rot2=0, yres=-30)
        >>> coord = GeoCoordinate(-1767039, 2940090)
        >>> rowcol = transform_geo(coord, aff)
        >>> rowcol
        RowColumn(row=2490, column=1618)
        >>> xy = transform_rc(rowcol, aff)
        >>> xy
        GeoCoordinate(x=-1767045, y=2940105)
    """
    # Spelled out for clarity
    col = (coord[0] - affine[0] - affine[3] * affine[2]) / affine[1]
    row = (coord[1] - affine[3] - affine[0] * affine[4]) / affine[5]

    return RowColumn(int(row), int(col))


def transform_rc(rowcol: RowColumn, affine: tuple) -> GeoCoordinate:
    """
    Perform the affine transformation from a row/col coordinate to a geospatial
    space.

    Pixel being defined by the upper left.

    Xgeo = GT(0) + Xpixel*GT(1) + Yline*GT(2)
    Ygeo = GT(3) + Xpixel*GT(4) + Yline*GT(5)

    From:
    http://www.gdal.org/gdal_datamodel.html

    Args:
        rowcol (sequence): (row, column) pair
        affine (sequence): transformation tuple

    Returns:
        GeoCoordinate namedtuple

    Examples:
        >>> ext, aff = ard_hv(5, 2)
        >>> aff
        GeoAffine(ulx=-1815585, xres=30, rot1=0, uly=3014805, rot2=0, yres=-30)
        >>> coord = GeoCoordinate(-1767039, 2940090)
        >>> rowcol = transform_geo(coord, aff)
        >>> rowcol
        RowColumn(row=2490, column=1618)
        >>> xy = transform_rc(rowcol, aff)
        >>> xy
        GeoCoordinate(x=-1767045, y=2940105)
    """
    # Spelled out for clarity
    x = affine[0] + rowcol[1] * affine[1] + rowcol[0] * affine[2]
    y = affine[3] + rowcol[1] * affine[4] + rowcol[0] * affine[5]

    return GeoCoordinate(x, y)


def split_extent(extent: Union[GeoExtent, RowColumnExtent]):
    """
    Helper func

    Splits an extent into it's UL and LR
    """
    if isinstance(extent, GeoExtent):
        t = GeoCoordinate
    elif isinstance(extent, RowColumnExtent):
        t = RowColumn
    else:
        raise TypeError

    return t(extent[0], extent[1]), t(extent[2], extent[3])


def transform_ext(extent: Union[GeoExtent, RowColumnExtent], affine: tuple):
    """

    """
    if isinstance(extent, GeoExtent):
        t = RowColumnExtent
        map_func = partial(transform_geo, affine=affine)
    elif isinstance(extent, RowColumnExtent):
        t = GeoExtent
        map_func = partial(transform_rc, affine=affine)
    else:
        raise TypeError

    return t(*chain(*map(map_func, split_extent(extent))))


def determine_hv(coord: GeoCoordinate, aff: tuple) -> Tuple[int, int]:
    """
    Determine the ARD tile H/V that contains the given coordinate.

    The 'H' corresponds to the column, and the 'V' corresponds to the row, so
    we can use a normal affine transformation. But because of normal usage, the
    'H' typically comes first.

    Args:
        coord (sequence): (x, y) coordinate pair
        aff:

    Returns:
        tuple, (h, v)
    """
    return transform_geo(coord, aff)[::-1]


def open_raster(path: str, readonly: bool=True):
    if readonly:
        return gdal.Open(path, gdal.GA_ReadOnly)
    else:
        return gdal.Open(path, gdal.GA_Update)


def raster_extent(path: str) -> GeoExtent:
    ds = open_raster(path)

    affine = raster_affine(path)
    rc_lr = RowColumn(ds.RasterYSize, ds.RasterXSize)

    geo_lr = transform_rc(rc_lr, affine)

    return GeoExtent(xmin=affine[0], xmax=geo_lr.x,
                     ymin=geo_lr.y, ymax=affine[3])


def raster_affine(path: str) -> tuple:
    """
    Retrieve the affine/GeoTransform from a raster
    """
    ds = open_raster(path)

    return ds.GetGeoTransform()


def raster_band(path: str, band: int=1):
    ds = open_raster(path)

    return ds.GetRasterBand(band).ReadAsArray()


def extract_geoextent(path: str, geo_extent: GeoExtent, band: int=1):
    affine = raster_affine(path)
    rc_ext = transform_ext(geo_extent, affine)

    return extract_rcextent(path, rc_ext, band)


def extract_rcextent(path: str, rc_extent: RowColumnExtent, band: int=1):
    ds = open_raster(path)

    ul, lr = split_extent(rc_extent)

    return ds.GetRasterBand(band).ReadAsArray(ul.column,
                                              ul.row,
                                              lr.column - ul.column,
                                              lr.row - ul.row)


def chipul(coord: GeoCoordinate, chip_aff: tuple) -> GeoCoordinate:
    """
    Chip defined as a 100x100 30m pixel area.

    Args:
        coord (sequence): (x, y) coordinate pair
        chip_aff: special affine that determines the bounds of data extraction and processing

    Returns:

    """
    # Flip it!
    rc = transform_geo(coord, chip_aff)
    return transform_rc(rc, chip_aff)


def extract_chip(path: str, coord: GeoCoordinate, chip_aff: tuple):
    """
    Chip defined as a 100x100 30m pixel area.

    Args:
        path:
        coord (sequence): (x, y) coordinate pair
        chip_aff: special affine that determines the bounds of data extraction and processing

    Returns:

    """
    chip_ul = chipul(coord, chip_aff)
    chip_ext = GeoExtent(chip_ul[0], chip_ul[1], chip_ul[0] + 3000, chip_ul[1] - 3000)

    return extract_geoextent(path, chip_ext)
