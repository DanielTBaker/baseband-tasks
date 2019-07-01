# Licensed under the GPLv3 - see LICENSE
"""Full-package tests of psrfits writing routines."""

import os

import pytest
import numpy as np
from astropy.time import Time, TimeDelta
from astropy.coordinates import SkyCoord, EarthLocation
from astropy.coordinates import Angle, Latitude, Longitude
import astropy.units as u

from ..io import psrfits

test_data = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'data')


class TestSetter:
    def setup(self):
        self.fold_data = os.path.join(test_data,
                                      "B1855+09.430.PUPPI.11y.x.sum.sm")
        self.reader = psrfits.open(self.fold_data, weighted=False)
        self.input_p_hdu = self.reader.ih.primary_hdu
        # init Primary
        self.p_hdu = psrfits.PSRFITSPrimaryHDU()

    def teardown(self):
        self.reader.close()

    def test_set_location(self):
        self.p_hdu.location = self.input_p_hdu.location
        assert self.p_hdu.header['ANT_X'] == self.input_p_hdu.header['ANT_X']
        assert self.p_hdu.header['ANT_Y'] == self.input_p_hdu.header['ANT_Y']
        assert self.p_hdu.header['ANT_Z'] == self.input_p_hdu.header['ANT_Z']

    def test_set_telescope(self):
        self.p_hdu.telescope = self.input_p_hdu.telescope
        assert (self.p_hdu.header['TELESCOP'] ==
                self.input_p_hdu.header['TELESCOP'])

    def test_set_start_time(self):
        self.p_hdu.start_time = self.input_p_hdu.start_time
        assert np.isclose(int(self.p_hdu.header['STT_IMJD']),
                          self.input_p_hdu.header['STT_IMJD'])
        assert np.isclose(int(self.p_hdu.header['STT_SMJD']),
                          self.input_p_hdu.header['STT_SMJD'])
        assert np.isclose(float(self.p_hdu.header['STT_OFFS']),
                          self.input_p_hdu.header['STT_OFFS'])
        assert self.p_hdu.header['DATE-OBS'].startswith(self.input_p_hdu.header['DATE-OBS'])

    def test_set_freq(self):
        self.p_hdu.frequency = self.input_p_hdu.frequency
        assert (self.p_hdu.header['OBSNCHAN'] ==
                self.input_p_hdu.header['OBSNCHAN'])
        assert (self.p_hdu.header['OBSFREQ'] ==
                self.input_p_hdu.header['OBSFREQ'])
        assert (self.p_hdu.header['OBSBW'] ==
                self.input_p_hdu.header['OBSBW'])

    def test_set_sideband(self):
        self.p_hdu.header['OBSBW'] = self.input_p_hdu.header['OBSBW']
        self.p_hdu.sideband = -self.input_p_hdu.sideband
        assert (self.p_hdu.header['OBSBW'] ==
                -self.input_p_hdu.header['OBSBW'])
        self.p_hdu.sideband = self.input_p_hdu.sideband
        assert (self.p_hdu.header['OBSBW'] ==
                self.input_p_hdu.header['OBSBW'])

    def test_set_mode(self):
        self.p_hdu.obs_mode = 'PSR'
        assert self.p_hdu.header['OBS_MODE'] == 'PSR'
        with pytest.raises(AssertionError):
            self.p_hdu.obs_mode = 'BASEBAND'

    def test_set_skycoord(self):
        self.p_hdu.ra = self.input_p_hdu.ra
        self.p_hdu.dec = self.input_p_hdu.dec
        assert (Longitude(self.p_hdu.header['RA'], unit=u.hourangle) ==
                Longitude(self.input_p_hdu.header['RA'], unit=u.hourangle))
        assert (Latitude(self.p_hdu.header['DEC'], unit=u.deg) ==
                Latitude(self.input_p_hdu.header['DEC'], unit=u.deg))
