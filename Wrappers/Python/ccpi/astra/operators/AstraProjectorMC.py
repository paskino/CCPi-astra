# -*- coding: utf-8 -*-
#    This work is independent part of the Core Imaging Library developed by
#    Visual Analytics and Imaging System Group of the Science Technology
#    Facilities Council, STFC
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

from ccpi.optimisation.operators import Operator, LinearOperator
from ccpi.framework import AcquisitionData, ImageData, DataContainer, ImageGeometry, AcquisitionGeometry
from ccpi.astra.processors import AstraForwardProjector, AstraBackProjector, \
     AstraForwardProjectorMC, AstraBackProjectorMC, AstraForwardProjector3D, \
     AstraBackProjector3D
from ccpi.astra.operators import AstraProjectorSimple     

class AstraProjectorMC(LinearOperator):
    """ASTRA Multichannel projector"""
    def __init__(self, geomv, geomp, device):
        super(AstraProjectorMC, self).__init__()
        
        # Store volume and sinogram geometries.
        self.sinogram_geometry = geomp
        self.volume_geometry = geomv
        
        self.fp = AstraForwardProjectorMC(volume_geometry=geomv,
                                        sinogram_geometry=geomp,
                                        proj_id=None,
                                        device=device)
        
        self.bp = AstraBackProjectorMC(volume_geometry=geomv,
                                        sinogram_geometry=geomp,
                                        proj_id=None,
                                        device=device)
                
        # Initialise empty for singular value.
        self.s1 = None    
    
    def direct(self, IM, out=None):
        self.fp.set_input(IM)
        
        if out is None:
            return self.fp.get_output()
        else:
            out.fill(self.fp.get_output())
    
    def adjoint(self, DATA, out=None):
#        self.bp.set_input(DATA)
        
        if out is None:
            return self.bp.get_output()
        else:
            out.fill(self.bp.get_output())    
    
    def domain_geometry(self):
        return self.volume_geometry
    
    def range_geometry(self):
        return self.sinogram_geometry    
    
    def calculate_norm(self):
                
        voxel_num_x = self.volume_geometry.voxel_num_x
        voxel_num_y = self.volume_geometry.voxel_num_y
        igtmp = ImageGeometry(voxel_num_x = voxel_num_x, voxel_num_y = voxel_num_y)
        
        geom_type = self.sinogram_geometry.geom_type
        angles = self.sinogram_geometry.angles
        pixels_num_h = self.sinogram_geometry.pixel_num_h
        
        agtmp = AcquisitionGeometry(geom_type, '2D',  angles, pixel_num_h = pixels_num_h)
        Atmp = AstraProjectorSimple(igtmp, agtmp, 'gpu')
              
        #TODO Approach with clone should be better but it doesn't work atm
        
        #igtmp = self.volume_geometry.clone()
        #agtmp = self.sinogram_geometry.clone()
        #igtmp.channels=1
        #agtmp.channels=1
        #igtmp.dimension_labels = ['angle','vertical']
        #agtmp.dimension_labels = ['angle','vertical']
        #Atmp = AstraProjectorSimple(igtmp, agtmp, self.fp.device)
        
        
        
        return Atmp.norm()    
    
#    def norm(self):
#        x0 = self.volume_geometry.allocate('random')
#        self.s1, sall, svec = LinearOperator.PowerMethod(self, 50, x0)
#        return self.s1
