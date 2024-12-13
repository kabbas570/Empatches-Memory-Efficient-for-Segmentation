### Importing Necessary Libraries

```python
import numpy as np 
import math
import tempfile
import shutil
import os
import cv2
```

### Class Definition: EMPatches_Effi_Seg_Inference
This class is responsible for:
- Managing temporary directories for patch extraction.
- Extracting patches from an image based on specified patch size, overlap, or stride.
- Cleaning up temporary files.

```python
class EMPatches_Effi_Seg_Inference(object):
    
    def __init__(self):
        self.temp_dir = None
        self.temp_dir_path = None

    def cleanup(self):
        # Deletes the temporary directory created for storing patches.
        if self.temp_dir:
            shutil.rmtree(self.temp_dir)
            self.temp_dir = None

    def extract_patches(self, data, patchsize, overlap=None, stride=None, vox=False, base_temp_dir=None):
        
        # Create a temporary directory for storing image patches
        if base_temp_dir is not None:
            self.temp_dir = tempfile.mkdtemp(dir=base_temp_dir)
        else:
            self.temp_dir = tempfile.mkdtemp()

        '''
        Parameters:
        - data: Array to extract patches from; supports 1D, 2D, or 3D data.
        - patchsize: Size of square patches to extract.
        - overlap: Overlap between patches as a percentage [0, 1].
        - stride: Step size between patches.
        - vox: Boolean flag for volumetric data.
        - base_temp_dir: Directory for temporary storage.

        Returns:
        - temp_dir: Directory where patches are saved.
        - indices: Indices of extracted patches.
        - Original Dimensions: Tuple of original data dimensions.
        '''

        height, width, depth = data.shape

        maxWindowSize = patchsize
        windowSizeX = min(maxWindowSize, width)
        windowSizeY = min(maxWindowSize, height)
        windowSizeZ = min(maxWindowSize, depth)

        if stride is not None:
            stepSizeX = stepSizeY = stepSizeZ = stride
        elif overlap is not None:
            overlapPercent = overlap

            windowOverlapX = int(math.floor(windowSizeX * overlapPercent))
            windowOverlapY = int(math.floor(windowSizeY * overlapPercent))
            windowOverlapZ = int(math.floor(windowSizeZ * overlapPercent))

            stepSizeX = windowSizeX - windowOverlapX
            stepSizeY = windowSizeY - windowOverlapY                
            stepSizeZ = windowSizeZ - windowOverlapZ                
        else:
            stepSizeX = stepSizeY = stepSizeZ = 1

        lastX, lastY, lastZ = width - windowSizeX, height - windowSizeY, depth - windowSizeZ
        xOffsets = list(range(0, lastX+1, stepSizeX))
        yOffsets = list(range(0, lastY+1, stepSizeY))
        zOffsets = list(range(0, lastZ+1, stepSizeZ))

        if len(xOffsets) == 0 or xOffsets[-1] != lastX:
            xOffsets.append(lastX)
        if len(yOffsets) == 0 or yOffsets[-1] != lastY:
            yOffsets.append(lastY)
        if len(zOffsets) == 0 or zOffsets[-1] != lastZ:
            zOffsets.append(lastZ)

        indices = []
        patch_index = 0

        for xOffset in xOffsets:
            for yOffset in yOffsets:
                patch_path = os.path.join(self.temp_dir, f"patch_{patch_index}.png")
                cv2.imwrite(patch_path, data[(slice(yOffset, yOffset+windowSizeY),
                                              slice(xOffset, xOffset+windowSizeX))])
                patch_index += 1    
                indices.append((yOffset, yOffset+windowSizeY, xOffset, xOffset+windowSizeX))

        return self.temp_dir, indices, (height, width, depth)
```

### Instantiating and Using the EMPatches_Effi_Seg_Inference Class
Here, we:
1. Create an instance of the class.
2. Specify paths and parameters for image and patches.

```python
emp = EMPatches_Effi_Seg_Inference()

# Directories and input image
output_path = "path to save segmentaiton mask" + "reconstructed_seg_mask.png"
image_path = "path to the input RGB image"
temp_dir = "Optional to save temporary patches"

image = cv2.imread(image_path)
patches_path, indices, org_shape = emp.extract_patches(image, patchsize=224, overlap=0.0, base_temp_dir=temp_dir)
```

### Simple Segmentation Model Implementation
This dummy segmentation model converts an RGB image to grayscale.

```python
from torch import nn

class Seg_Model(nn.Module):
    def __init__(self):
        super().__init__()

    def forward(self, x):
        return cv2.cvtColor(x, cv2.COLOR_RGB2GRAY)

model = Seg_Model()  
```

### Reconstructing the Segmentation Mask
The patches are passed through the model, and the segmentation results are stitched back to form the full image.

```python
reconstructed_seg_mask = np.zeros(org_shape, dtype=np.uint8)

# Iterate through patch files
for i, patch_file in enumerate(sorted(os.listdir(patches_path))):
    patch_path = os.path.join(patches_path, patch_file)
    patch = cv2.imread(patch_path)
    y = model(patch)
    y = np.stack((y,)*3, axis=-1)  # Repeat grayscale to create a 3-channel image
    y_start, y_end, x_start, x_end = indices[i]
    reconstructed_seg_mask[y_start:y_end, x_start:x_end] = y
    del patch, y

cv2.imwrite(output_path, reconstructed_seg_mask)
print(f"Reconstructed segmentation saved to: {output_path}")

# Clean up temporary patches
_ = emp.cleanup()
```
