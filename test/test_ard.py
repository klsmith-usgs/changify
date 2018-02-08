import numpy as np

from changify import ard, app


config = app.Config

tst_file = ('/vsitar'
            '/test'
            '/data'
            '/h05v02'
            '/LT05_CU_005002_19850302_20170711_C01_V01_SR.tar'
            '/LT05_CU_005002_19850302_20170711_C01_V01_SRB3.tif')

tst_filename = tst_file.split('/')[-2]
tst_path = r'/test/data'

tst_aff = (-1815585, 30, 0, 3014805, 0, -30)
tst_coord = ard.GeoCoordinate(-1701195, 3005565)
tst_rc = ard.RowColumn(308, 3813)
tst_rcext = ard.RowColumnExtent(300, 3800, 301, 3801)
tst_geoext = ard.GeoExtent(-1701585.0, 3005805.0, -1701555.0, 3005775.0)


def test_ardhv():
    conus = ard.GeoExtent(**config['conus-extent'])
    ext, aff = ard.ard_hv(5, 2, conus)

    assert ext == (-1815585, 3014805, -1665585, 2864805)
    assert aff == tst_aff


def test_fifteen_offset():
    assert ard.fifteen_offset(1) == 15
    assert ard.fifteen_offset(-1) == -15


def test_transform_geo():
    assert ard.transform_geo(tst_coord, tst_aff) == tst_rc


def test_transform_rc():
    assert ard.transform_rc(tst_rc, tst_aff) == tst_coord


def test_split_extent():
    pt1, pt2 = ard.split_extent(tst_geoext)

    assert isinstance(pt1, ard.GeoCoordinate)
    assert isinstance(pt2, ard.GeoCoordinate)
    assert pt1 == (-1701585.0, 3005805.0)
    assert pt2 == (-1701555.0, 3005775.0)


def test_transform_ext():
    rc_ext = ard.transform_ext(tst_geoext, tst_aff)
    geo_ext = ard.transform_ext(tst_rcext, tst_aff)

    assert rc_ext == tst_rcext
    assert geo_ext == tst_geoext


def test_open_raster():
    ds = ard.open_raster(tst_file)

    assert ds is not None


def test_raster_affine():
    aff = ard.raster_affine(tst_file)

    assert aff == tst_aff


def test_extract_geoextent():
    ext = ard.GeoExtent(-1701585.0, 3005805.0, -1701555.0, 3005775.0)

    assert ard.extract_geoextent(tst_file, ext) == 8801


def test_extract_chip():
    coord = ard.GeoCoordinate(-1707541, 2996742)
    aff = config['conus-chipaff']

    np.array_equal(ard.extract_chip(tst_file, coord, aff),
                   np.full(shape=(100, 100), fill_value=-9999))


def test_determine_hv():
    assert ard.determine_hv(tst_coord, config['conus-tileaff']) == (5, 2)


def test_filter_reg():
    assert ard.filter_reg(tst_filename, 'CU') is True
    assert ard.filter_reg(tst_filename, 'AK') is False


def test_filter_tar():
    assert ard.filter_tar(tst_filename, 'SR') is True
    assert ard.filter_tar(tst_filename, 'TA') is False


def test_filter_date():
    assert ard.filter_date(tst_filename, '1984-01-01/1985-03-02') is True
    assert ard.filter_date(tst_filename, '1985-03-02/1990-01-01') is True
    assert ard.filter_date(tst_filename, '1985-03-03/1987-01-01') is False


def test_vsipath():
    layer = ard.vsipath(r'test/data/h05v02/LT05_CU_005002_19850302_20170711_C01_V01_BT.tar',
                        'thermals',
                        config['file-specs'],
                        'BT')

    ds = ard.open_raster(layer)

    assert ds is not None


def test_tarfiles():
    files = ard.tarfiles(r'test/data/h05v02',
                         '1980-01-01/2014-01-01',
                         'CU',
                         'SR')

    assert sorted(files) == ['LE07_CU_005002_19991020_20170712_C01_V01_SR.tar',
                             'LT05_CU_005002_19850302_20170711_C01_V01_SR.tar']
