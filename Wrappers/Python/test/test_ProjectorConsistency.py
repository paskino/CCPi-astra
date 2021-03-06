# -*- coding: utf-8 -*-
#  CCP in Tomographic Imaging (CCPi) Core Imaging Library (CIL).

#   Copyright 2017 UKRI-STFC
#   Copyright 2017 University of Manchester

#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at

#   http://www.apache.org/licenses/LICENSE-2.0

#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

from cil.framework import ImageGeometry, AcquisitionGeometry

from cil.plugins.astra.operators import AstraProjectorSimple, AstraProjector3DSimple, AstraProjectorFlexible
from cil.plugins.astra.operators import ProjectionOperator

import unittest
import numpy as np

try:
    import astra
    has_astra = True
    
except ImportError as re:
    print (re)
    has_astra = False

class TestAstraConeBeamProjectors(unittest.TestCase):
    def setUp(self): 
        #%% Setup Geometry
        voxel_num_xy = 255
        voxel_num_z = 15
        self.cs_ind = (voxel_num_z-1)//2

        mag = 2
        src_to_obj = 50
        src_to_det = src_to_obj * mag

        pix_size = 0.2
        det_pix_x = voxel_num_xy
        det_pix_y = voxel_num_z

        num_projections = 180
        angles = np.linspace(0, np.pi, num=num_projections, endpoint=False)

        self.ag = AcquisitionGeometry.create_Cone3D([0,-src_to_obj,0],[0,src_to_det-src_to_obj,0])\
                                     .set_angles(angles, angle_unit='radian')\
                                     .set_panel((det_pix_x,det_pix_y), (pix_size,pix_size))\
                                     .set_labels(['vertical','angle','horizontal'])

        self.ag_slice = AcquisitionGeometry.create_Cone2D([0,-src_to_obj],[0,src_to_det-src_to_obj])\
                                           .set_angles(angles, angle_unit='radian')\
                                           .set_panel(det_pix_x, pix_size)\
                                           .set_labels(['angle','horizontal'])

        self.ig_2D = self.ag_slice.get_ImageGeometry()
        self.ig_3D = self.ag.get_ImageGeometry()

        #%% Create phantom
        kernel_size = voxel_num_xy
        kernel_radius = (kernel_size - 1) // 2
        y, x = np.ogrid[-kernel_radius:kernel_radius+1, -kernel_radius:kernel_radius+1]

        circle1 = [5,0,0] #r,x,y
        dist1 = ((x - circle1[1])**2 + (y - circle1[2])**2)**0.5

        circle2 = [5,100,0] #r,x,y
        dist2 = ((x - circle2[1])**2 + (y - circle2[2])**2)**0.5

        circle3 = [25,0,100] #r,x,y
        dist3 = ((x - circle3[1])**2 + (y - circle3[2])**2)**0.5

        mask1 =(dist1 - circle1[0]).clip(0,1) 
        mask2 =(dist2 - circle2[0]).clip(0,1) 
        mask3 =(dist3 - circle3[0]).clip(0,1) 
        phantom = 1 - np.logical_and(np.logical_and(mask1, mask2),mask3)

        self.golden_data = self.ig_3D.allocate(0)
        for i in range(4):
            self.golden_data.fill(array=phantom, vertical=7+i)

        self.golden_data_cs = self.golden_data.subset(vertical=self.cs_ind, force=True)

    @unittest.skipUnless(has_astra, "Astra not available")
    def test_consistency(self):
    
        # #%% AstraProjectorSimple cpu
        ig = self.ig_2D.copy()
        ag = self.ag_slice.copy()

        A = AstraProjectorSimple(ig, ag, device='cpu')
        fp = A.direct(self.golden_data_cs)
        bp = A.adjoint(fp)

        # #%% AstraProjectorFlexible
        ig = self.ig_3D.copy()
        ag = self.ag.copy()

        A = AstraProjector3DSimple(ig, ag)
        flex_fp = A.direct(self.golden_data)
        flex_bp = A.adjoint(flex_fp)

        #comparision foward projection
        fp_flex_0 = flex_fp.subset(vertical=self.cs_ind, force=True)
        fp_flex_2 = flex_fp.subset(vertical=self.cs_ind-3, force=True)

        zeros = self.ag_slice.allocate(0)
        np.testing.assert_allclose(fp_flex_0.as_array(),fp.as_array(), atol=0.8)
        np.testing.assert_allclose(fp_flex_2.as_array(),zeros.as_array())

        #comparision back projection
        bp_flex_0 = flex_bp.subset(vertical=self.cs_ind, force=True)
        bp_flex_1 = flex_bp.subset(vertical=self.cs_ind+3, force=True)
        bp_flex_2 = flex_bp.subset(vertical=self.cs_ind-3, force=True)

        zeros = self.ig_2D.allocate(0)
        np.testing.assert_allclose(bp_flex_0.as_array(),bp.as_array(),atol=12)
        np.testing.assert_allclose(bp_flex_1.as_array(),bp.as_array(),atol=25)
        np.testing.assert_allclose(bp_flex_2.as_array(),zeros.as_array())
        
    @unittest.skipUnless(has_astra and astra.use_cuda(), "Astra GPU not available")
    def test_3D(self):
        #%% AstraProjectorSimple gpu
        ig = self.ig_3D.copy()
        ag = self.ag.copy()

        A = AstraProjector3DSimple(ig, ag)
        fp = A.direct(self.golden_data)
        bp = A.adjoint(fp)

        # #%% AstraProjectorFlexible
        ig = self.ig_3D.copy()
        ag = self.ag.copy()

        A = AstraProjector3DSimple(ig, ag)
        flex_fp = A.direct(self.golden_data)
        flex_bp = A.adjoint(fp)

        #comparision foward projection
        fp_0 = fp.subset(vertical=self.cs_ind, force=True)
        fp_1 = fp.subset(vertical=self.cs_ind+3, force=True)
        fp_2 = fp.subset(vertical=self.cs_ind-3, force=True)

        fp_flex_0 = flex_fp.subset(vertical=self.cs_ind, force=True)
        fp_flex_1 = flex_fp.subset(vertical=self.cs_ind+3, force=True)
        fp_flex_2 = flex_fp.subset(vertical=self.cs_ind-3, force=True)

        np.testing.assert_allclose(fp_flex_0.as_array(),fp_0.as_array())
        np.testing.assert_allclose(fp_flex_1.as_array(),fp_1.as_array())
        np.testing.assert_allclose(fp_flex_2.as_array(),fp_2.as_array())

        #comparision back projection
        bp_0 = bp.subset(vertical=self.cs_ind, force=True)
        bp_1 = bp.subset(vertical=self.cs_ind+3, force=True)
        bp_2 = bp.subset(vertical=self.cs_ind-3, force=True)

        bp_flex_0 = flex_bp.subset(vertical=self.cs_ind, force=True)
        bp_flex_1 = flex_bp.subset(vertical=self.cs_ind+3, force=True)
        bp_flex_2 = flex_bp.subset(vertical=self.cs_ind-3, force=True)

        np.testing.assert_allclose(bp_flex_0.as_array(),bp_0.as_array())
        np.testing.assert_allclose(bp_flex_1.as_array(),bp_1.as_array())
        np.testing.assert_allclose(bp_flex_2.as_array(),bp_2.as_array())


    @unittest.skipUnless(has_astra and astra.use_cuda(), "Astra not built with CUDA")
    def test_2D(self):
        
        # #%% AstraProjectorSimple cpu
        ig = self.ig_2D.copy()
        ag = self.ag_slice.copy()

        A = AstraProjectorSimple(ig, ag, device='cpu')
        fp = A.direct(self.golden_data_cs)
        bp = A.adjoint(fp)

        #%% AstraProjectorSimple gpu
        ig = self.ig_2D.copy()
        ag = self.ag_slice.copy()

        A = AstraProjectorSimple(ig, ag, device='gpu')
        fp_gpu = A.direct(self.golden_data_cs)
        bp_gpu = A.adjoint(fp_gpu)

        np.testing.assert_allclose(fp_gpu.as_array(),fp.as_array(),atol=0.8)
        np.testing.assert_allclose(bp_gpu.as_array(),bp.as_array(),atol=12)

        # #%% AstraProjectorFlexible as a 2D
        ig = self.ig_2D.copy()
        ag = self.ag_slice.copy()

        A = AstraProjectorFlexible(ig, ag)
        fp_flex = A.direct(self.golden_data_cs)
        bp_flex = A.adjoint(fp_flex)

        np.testing.assert_allclose(fp_flex.as_array(),fp.as_array(),atol=0.8)
        np.testing.assert_allclose(bp_flex.as_array(),bp.as_array(),atol=12)

class TestAstraParallelBeamProjectors(unittest.TestCase):
    def setUp(self): 
        #%% Setup Geometry
        voxel_num_xy = 255
        voxel_num_z = 15
        self.cs_ind = (voxel_num_z-1)//2

        pix_size = 0.2
        det_pix_x = voxel_num_xy
        det_pix_y = voxel_num_z

        num_projections = 180
        angles = np.linspace(0, np.pi, num=num_projections, endpoint=False)

        self.ag = AcquisitionGeometry.create_Parallel3D()\
                                     .set_angles(angles, angle_unit='radian')\
                                     .set_panel((det_pix_x,det_pix_y), (pix_size,pix_size))\
                                     .set_labels(['vertical','angle','horizontal'])

        self.ag_slice = AcquisitionGeometry.create_Parallel2D()\
                                           .set_angles(angles, angle_unit='radian')\
                                           .set_panel(det_pix_x, pix_size)\
                                           .set_labels(['angle','horizontal'])

        self.ig_2D = self.ag_slice.get_ImageGeometry()
        self.ig_3D = self.ag.get_ImageGeometry()

        #%% Create phantom
        kernel_size = voxel_num_xy
        kernel_radius = (kernel_size - 1) // 2
        y, x = np.ogrid[-kernel_radius:kernel_radius+1, -kernel_radius:kernel_radius+1]

        circle1 = [5,0,0] #r,x,y
        dist1 = ((x - circle1[1])**2 + (y - circle1[2])**2)**0.5

        circle2 = [5,100,0] #r,x,y
        dist2 = ((x - circle2[1])**2 + (y - circle2[2])**2)**0.5

        circle3 = [25,0,100] #r,x,y
        dist3 = ((x - circle3[1])**2 + (y - circle3[2])**2)**0.5

        mask1 =(dist1 - circle1[0]).clip(0,1) 
        mask2 =(dist2 - circle2[0]).clip(0,1) 
        mask3 =(dist3 - circle3[0]).clip(0,1) 
        phantom = 1 - np.logical_and(np.logical_and(mask1, mask2),mask3)

        self.golden_data = self.ig_3D.allocate(0)
        for i in range(4):
            self.golden_data.fill(array=phantom, vertical=7+i)

        self.golden_data_cs = self.golden_data.subset(vertical=self.cs_ind, force=True)
    @unittest.skipUnless(has_astra and astra.use_cuda(), "Astra not built with CUDA")
    def test_consistency(self):
    
        # #%% AstraProjectorSimple cpu
        ig = self.ig_2D.copy()
        ag = self.ag_slice.copy()

        A = AstraProjectorSimple(ig, ag, device='cpu')
        fp = A.direct(self.golden_data_cs)
        bp = A.adjoint(fp)

        # #%% AstraProjectorFlexible
        ig = self.ig_3D.copy()
        ag = self.ag.copy()

        A = AstraProjector3DSimple(ig, ag)
        flex_fp = A.direct(self.golden_data)
        flex_bp = A.adjoint(flex_fp)

        #comparision foward projection
        fp_flex_0 = flex_fp.subset(vertical=self.cs_ind, force=True)
        fp_flex_1 = flex_fp.subset(vertical=self.cs_ind+3, force=True)
        fp_flex_2 = flex_fp.subset(vertical=self.cs_ind-3, force=True)

        zeros = self.ag_slice.allocate(0)
        np.testing.assert_allclose(fp_flex_0.as_array(),fp.as_array(), atol=0.8)
        np.testing.assert_allclose(fp_flex_1.as_array(),fp.as_array(), atol=0.8)
        np.testing.assert_allclose(fp_flex_2.as_array(),zeros.as_array())

        #comparision back projection
        bp_flex_0 = flex_bp.subset(vertical=self.cs_ind, force=True)
        bp_flex_1 = flex_bp.subset(vertical=self.cs_ind+3, force=True)
        bp_flex_2 = flex_bp.subset(vertical=self.cs_ind-3, force=True)

        zeros = self.ig_2D.allocate(0)
        np.testing.assert_allclose(bp_flex_0.as_array(),bp.as_array(),atol=12)
        np.testing.assert_allclose(bp_flex_1.as_array(),bp.as_array(),atol=12)
        np.testing.assert_allclose(bp_flex_2.as_array(),zeros.as_array())
    @unittest.skipUnless(has_astra and astra.use_cuda(), "Astra not built with CUDA")
    def test_3D(self):
        #%% AstraProjectorSimple gpu
        ig = self.ig_3D.copy()
        ag = self.ag.copy()

        A = AstraProjector3DSimple(ig, ag)
        fp = A.direct(self.golden_data)
        bp = A.adjoint(fp)

        # #%% AstraProjectorFlexible
        ig = self.ig_3D.copy()
        ag = self.ag.copy()

        A = AstraProjector3DSimple(ig, ag)
        flex_fp = A.direct(self.golden_data)
        flex_bp = A.adjoint(fp)

        #comparision foward projection
        fp_0 = fp.subset(vertical=self.cs_ind, force=True)
        fp_1 = fp.subset(vertical=self.cs_ind+3, force=True)
        fp_2 = fp.subset(vertical=self.cs_ind-3, force=True)

        fp_flex_0 = flex_fp.subset(vertical=self.cs_ind, force=True)
        fp_flex_1 = flex_fp.subset(vertical=self.cs_ind+3, force=True)
        fp_flex_2 = flex_fp.subset(vertical=self.cs_ind-3, force=True)

        np.testing.assert_allclose(fp_flex_0.as_array(),fp_0.as_array())
        np.testing.assert_allclose(fp_flex_1.as_array(),fp_1.as_array())
        np.testing.assert_allclose(fp_flex_2.as_array(),fp_2.as_array())

        #comparision back projection
        bp_0 = bp.subset(vertical=self.cs_ind, force=True)
        bp_1 = bp.subset(vertical=self.cs_ind+3, force=True)
        bp_2 = bp.subset(vertical=self.cs_ind-3, force=True)

        bp_flex_0 = flex_bp.subset(vertical=self.cs_ind, force=True)
        bp_flex_1 = flex_bp.subset(vertical=self.cs_ind+3, force=True)
        bp_flex_2 = flex_bp.subset(vertical=self.cs_ind-3, force=True)

        np.testing.assert_allclose(bp_flex_0.as_array(),bp_0.as_array())
        np.testing.assert_allclose(bp_flex_1.as_array(),bp_1.as_array())
        np.testing.assert_allclose(bp_flex_2.as_array(),bp_2.as_array())


    @unittest.skipUnless(has_astra and astra.use_cuda(), "Astra not built with CUDA")
    def test_2D(self):
        
        # #%% AstraProjectorSimple cpu
        ig = self.ig_2D.copy()
        ag = self.ag_slice.copy()

        A = AstraProjectorSimple(ig, ag, device='cpu')
        fp = A.direct(self.golden_data_cs)
        bp = A.adjoint(fp)

        #%% AstraProjectorSimple gpu
        ig = self.ig_2D.copy()
        ag = self.ag_slice.copy()

        A = AstraProjectorSimple(ig, ag, device='gpu')
        fp_gpu = A.direct(self.golden_data_cs)
        bp_gpu = A.adjoint(fp_gpu)

        np.testing.assert_allclose(fp_gpu.as_array(),fp.as_array(),atol=0.8)
        np.testing.assert_allclose(bp_gpu.as_array(),bp.as_array(),atol=12)

        # #%% AstraProjectorFlexible as a 2D
        ig = self.ig_2D.copy()
        ag = self.ag_slice.copy()

        A = AstraProjectorFlexible(ig, ag)
        fp_flex = A.direct(self.golden_data_cs)
        bp_flex = A.adjoint(fp_flex)

        np.testing.assert_allclose(fp_flex.as_array(),fp.as_array(),atol=0.8)
        np.testing.assert_allclose(bp_flex.as_array(),bp.as_array(),atol=12)

    