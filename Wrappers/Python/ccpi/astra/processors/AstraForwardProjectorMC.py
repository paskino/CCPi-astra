import ccpi.cfg as cfg
if cfg.run_with_cupy:
    try:
        import cupy
    except:
        print("There is no cupy installed")  

from ccpi.framework import AcquisitionData

from ccpi.astra.processors import AstraForwardProjector

import astra


class AstraForwardProjectorMC(AstraForwardProjector):
    '''AstraForwardProjector Multi channel
    
    Forward project ImageData to AcquisitionDataSet using ASTRA proj_id.
    
    Input: ImageDataSet
    Parameter: proj_id
    Output: AcquisitionData
    '''
    def check_input(self, dataset):
        if dataset.number_of_dimensions == 2 or \
           dataset.number_of_dimensions == 3 or \
           dataset.number_of_dimensions == 4:
               return True
        else:
            raise ValueError("Expected input dimensions is 2 or 3, got {0}"\
                             .format(dataset.number_of_dimensions))
    
    def process(self, out=None):
        IM = self.get_input()
        #create the output AcquisitionData
        DATA = AcquisitionData(geometry=self.sinogram_geometry)
        
        if cfg.run_with_cupy:        
            tmp_IM = cupy.asnumpy(IM.as_array())
            tmp_DATA = cupy.asnumpy(DATA.as_array())
        
            for k in range(DATA.geometry.channels):
                sinogram_id, tmp_DATA[k] = astra.create_sino(tmp_IM[k], 
                                                            self.proj_id)
                astra.data2d.delete(sinogram_id)
            DATA.array = cupy.array(tmp_DATA)                                               
        else:  
            for k in range(DATA.geometry.channels):                                              
                sinogram_id, DATA.as_array()[k] = astra.create_sino(IM.as_array()[k], self.proj_id)
                astra.data2d.delete(sinogram_id)
        
        if self.device == 'cpu':
            ret = DATA
        else:
            if self.sinogram_geometry.geom_type == 'cone':
                ret = DATA
            else:
                 scaling = 1.0 #(1.0/self.volume_geometry.voxel_size_x) 
                 ret = scaling*DATA
        
        if out is None:
            return ret
        else:
            out.fill(ret)