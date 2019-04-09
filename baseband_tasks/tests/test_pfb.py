# Licensed under the GPLv3 - see LICENSE
"""Tests of the polyphase filterbank module."""
import os

import pytest
import numpy as np
from numpy.testing import assert_allclose

import astropy.units as u
from astropy.time import Time

from baseband_tasks.generators import NoiseGenerator
from baseband_tasks.pfb import (
    sinc_hamming, PolyphaseFilterBankSamples, PolyphaseFilterBank,
    InversePolyphaseFilterBank)


test_data = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'data')


class TestSincHamming:
    def setup(self):
        a = np.loadtxt(os.path.join(
            test_data, 'bGDSP_U1_0032_T12_W095_get_pfb_coeffs.txt'))
        self.guppi_ppf = a.reshape(8, -1).T.reshape(12, 64)

    def test_guppi(self):
        model = sinc_hamming(12, 64, sinc_scale=0.95)
        assert_allclose(model, self.guppi_ppf)


class TestBasics:
    def setup(self):
        self.nh = NoiseGenerator(shape=(2500 * 2048,),
                                 start_time=Time('2010-01-01'),
                                 sample_rate=1.*u.kHz, seed=12345,
                                 samples_per_frame=128, dtype='f8')
        self.nc = NoiseGenerator(shape=(2500 * 2048,),
                                 start_time=Time('2010-01-01'),
                                 sample_rate=1.*u.kHz, seed=12345,
                                 samples_per_frame=128, dtype='c16')
        self.n_tap = 4
        self.n_chan = 2048
        n = self.n_tap * self.n_chan
        r = self.n_tap
        x = r * np.linspace(-0.5, 0.5, n, endpoint=False)
        self.pfb = (np.sinc(x) * np.hamming(4 * 2048)).reshape(4, 2048)

    @pytest.mark.parametrize('offset', (0, 1000))
    def test_understanding(self, offset):
        """Stepping or frequency selection should give same answer.

        Often think of PFB as multiplying with an array that is, e.g.,
        4 times larger, then FFTing and taking every 4th frequency.

        But this is equivalent to, after multiplication, summing 4
        subsequent arrays and taking the FT of that.
        """
        self.nh.seek(offset * 2048)
        # First check for real data.
        d = self.nh.read(5 * 2048).reshape(-1, 2048)
        hd = self.pfb * d[:4]
        ft1_hd = np.fft.rfft(hd.ravel())[::4]
        ft2_hd = np.fft.rfft(hd.sum(0))
        assert_allclose(ft1_hd, ft2_hd)

        # Check actual implementations.
        pfb = PolyphaseFilterBankSamples(self.nh, self.pfb)
        pfb.seek(offset)
        ft_pfb = pfb.read(2)
        assert_allclose(ft_pfb[0], ft2_hd)
        assert_allclose(ft_pfb[1], np.fft.rfft((self.pfb * d[1:]).sum(0)))
        pfb2 = PolyphaseFilterBank(self.nh, self.pfb)
        pfb2.seek(offset)
        ft_pfb2 = pfb2.read(2)
        assert_allclose(ft_pfb2, ft_pfb)

    @pytest.mark.parametrize('offset', (0, 1000))
    def test_understanding_complex(self, offset):
        # Check above holds for complex too.
        self.nc.seek(offset * 2048)
        c = self.nc.read(4 * 2048).reshape(-1, 2048)
        hc = self.pfb * c
        ft1_hc = np.fft.fft(hc.ravel())[::4]
        ft2_hc = np.fft.fft(hc.sum(0))
        assert_allclose(ft1_hc, ft2_hc)

        # And check actual implementation.
        pfb = PolyphaseFilterBankSamples(self.nc, self.pfb)
        pfb.seek(offset)
        ft_pfb = pfb.read(1)[0]
        assert_allclose(ft_pfb, ft2_hc)
        pfb2 = PolyphaseFilterBank(self.nc, self.pfb)
        pfb2.seek(offset)
        ft_pfb2 = pfb2.read(1)[0]
        assert_allclose(ft_pfb2, ft2_hc)

    def test_inversion_understanding(self):
        n_sample = 128
        self.nh.seek(3 * 2048)
        d_in = self.nh.read(n_sample * 2048).reshape(-1, 2048)
        pfb = PolyphaseFilterBank(self.nh, self.pfb,
                                  samples_per_frame=n_sample)
        ft_pfb = pfb.read(n_sample+3)
        # Dechannelize.
        d_pfb = np.fft.irfft(ft_pfb, axis=1)
        # Deconvolve.
        ft_dec = np.fft.rfft(d_pfb, axis=0)
        ft_dec /= pfb._ft_response_conj
        d_out = np.fft.irfft(ft_dec, axis=0, n=d_pfb.shape[0])
        d_out = d_out[3:]
        # We cannot hope to deconvolve near the edges, which means we loose
        # the middle samples.
        assert_allclose(d_in[32:-32, :950], d_out[32:-32, :950], atol=0.01)
        assert_allclose(d_in[32:-32, 1100:], d_out[32:-32, 1100:], atol=0.01)

    def test_inversion(self):
        self.nh.seek(3 * 2048)
        d_in = self.nh.read(128 * 2048).reshape(-1, 2048)
        pfb = PolyphaseFilterBank(self.nh, self.pfb)
        ipfb = InversePolyphaseFilterBank(pfb, self.pfb, sn=1e9, n=2048,
                                          samples_per_frame=128*2048,
                                          dtype=self.nh.dtype)
        d_out = ipfb.read(128 * 2048).reshape(-1, 2048)
        assert_allclose(d_in[32:-32, :950], d_out[32:-32, :950], atol=0.01)
        assert_allclose(d_in[32:-32, 1100:], d_out[32:-32, 1100:], atol=0.01)
