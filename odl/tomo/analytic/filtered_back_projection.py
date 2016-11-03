# Copyright 2014-2016 The ODL development group
#
# This file is part of ODL.
#
# ODL is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ODL is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ODL.  If not, see <http://www.gnu.org/licenses/>.

# Imports for common Python 2/3 codebase
from __future__ import print_function, division, absolute_import
from future import standard_library
standard_library.install_aliases()

import numpy as np
from odl.discr import ResizingOperator
from odl.trafos import FourierTransform, PYFFTW_AVAILABLE


__all__ = ('fbp_op',)


def fbp_op(ray_trafo, padding=True):
    """Create Filtered BackProjection from a ray transform.

    Parameters
    ----------
    ray_trafo : `RayTransform`

    padding : bool
        If the data space should be zero padded.

    Returns
    -------
    fbp : `Operator`
        Approximate inverse operator of ``ray_trafo``.
    """
    impl = 'pyfftw' if PYFFTW_AVAILABLE else 'numpy'
    alen = ray_trafo.geometry.motion_params.length

    if ray_trafo.domain.ndim == 2:
        # Define ramp filter
        def fft_filter(x):
            return np.sqrt(x[1]**2) / (2 * alen)

        # Define (padded) fourier transform
        if padding:
            # Define padding operator
            ran_shp = (ray_trafo.range.shape[0],
                       ray_trafo.range.shape[1] * 2 - 1)
            resizing = ResizingOperator(ray_trafo.range, ran_shp=ran_shp)

            fourier = FourierTransform(resizing.range, axes=1, impl=impl)
            fourier = fourier * resizing
        else:
            fourier = FourierTransform(ray_trafo.range, axes=1, impl=impl)

    elif ray_trafo.domain.ndim == 3:
        # Find the direction that the filter should be taken in
        du = ray_trafo.geometry.det_init_axes[0]
        dv = ray_trafo.geometry.det_init_axes[1]
        axis = ray_trafo.geometry.axis
        det_normal = np.cross(du, dv)
        rot_dir = np.cross(axis, det_normal)
        c = np.array([np.vdot(rot_dir, du), np.vdot(rot_dir, dv)])
        cnorm = np.linalg.norm(c)
        assert cnorm != 0
        c /= cnorm

        # Define ramp filter
        def fft_filter(x):
            return np.abs(c[0] * x[1] + c[1] * x[2]) / (2 * alen)

        # Define (padded) fourier transform
        if padding:
            # Define padding operator
            ran_shp = (ray_trafo.range.shape[0],
                       ray_trafo.range.shape[1] * 2 - 1,
                       ray_trafo.range.shape[2] * 2 - 1)
            resizing = ResizingOperator(ray_trafo.range, ran_shp=ran_shp)

            fourier = FourierTransform(resizing.range, axes=[1, 2], impl=impl)
            fourier = fourier * resizing
        else:
            fourier = FourierTransform(ray_trafo.range, axes=[1, 2], impl=impl)
    else:
        raise NotImplementedError('FBP only implemented in 2d and 3d')

    # Create ramp in the detector direction
    ramp_function = fourier.range.element(fft_filter)

    # Create ramp filter via the
    # convolution formula with fourier transforms
    ramp_filter = fourier.inverse * ramp_function * fourier

    # Create filtered backprojection by composing the backprojection
    # (adjoint) with the ramp filter. Also apply a scaling.
    return ray_trafo.adjoint * ramp_filter


if __name__ == '__main__':
    # pylint: disable=wrong-import-position
    from odl.util.testutils import run_doctests
    run_doctests()
