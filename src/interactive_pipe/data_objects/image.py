import numpy as np
from pathlib import Path
from typing import Any, Optional
import logging
image_backends = []

IMAGE_BACKEND_PILLOW = "pillow"
IMAGE_BACKEND_OPENCV= "opencv"
IMAGE_BACKENDS = [IMAGE_BACKEND_PILLOW, IMAGE_BACKEND_OPENCV]

try:
    import cv2
    image_backends.append(IMAGE_BACKEND_OPENCV)
except:
    logging.info("cv2 is not available")

try:
    from PIL import Image as PilImage
    image_backends.append(IMAGE_BACKEND_PILLOW)
except:
    logging.info("PIL is not available")
assert len(image_backends)>0

from data_objects.data import Data
# TODO: can we get rid of cv2? use lighter PIL instead


    
class Image(Data):
    def __init__(self, data, title="") -> None:
        super().__init__(data)
        self.title=title
    def _set_file_extensions(self):
        self.file_extensions = [".png", ".jpg", ".tif"]
    def _save(self, path: Path):
        self.save_image(self.data, self.append_with_stem(path, self.title))
    def _load(self, path: Path):
        return self.load_image(path)
    
    @staticmethod
    def save_image(data, path: Path, precision=8, backend=None):
        if backend is None:
            backend = IMAGE_BACKEND_PILLOW
        assert backend in IMAGE_BACKENDS
        if backend == IMAGE_BACKEND_OPENCV:
            Image.save_image_cv2(data, path, precision)
        if backend == IMAGE_BACKEND_PILLOW:
            Image.save_image_PIL(data, path, precision)
    
    @staticmethod
    def rescale_dynamic(data, precision=8):
        amplitude = 2**precision-1
        return np.round(data*amplitude).clip(0, amplitude)

    @staticmethod
    def save_image_cv2(data, path: Path, precision=8):
        assert isinstance(path, Path)
        out = Image.rescale_dynamic(data, precision=precision)
        out = out.astype(np.uint8 if precision == 8 else np.uint16)
        out = cv2.cvtColor(out, cv2.COLOR_BGR2RGB)
        cv2.imwrite(str(path), out)
    
    @staticmethod
    def save_image_PIL(data, path: Path, precision=8):
        assert precision == 8
        assert isinstance(path, Path)
        out = Image.rescale_dynamic(data, precision=precision)
        out = out.astype(np.uint8)  # PIL requires image data in uint8 format
        out = PilImage.fromarray(out, 'RGB')
        out.save(str(path))
    

    @staticmethod
    def load_image_cv2(path: Path, precision=8):
        img = cv2.imread(str(path))
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        return img / (2.**precision-1)  # scale image data to [0, 1]

    @staticmethod
    def load_image_PIL(path: Path, precision=8):
        img = PilImage.open(path)
        return np.array(img) / (2.**precision-1)  # scale image data to [0, 1]
    
    @staticmethod
    def load_image(path: Path, precision=8, backend=None):
        if backend is None:
            backend = IMAGE_BACKEND_PILLOW
        assert backend in IMAGE_BACKENDS
        if backend == IMAGE_BACKEND_OPENCV:
            return Image.load_image_cv2(path)
        if backend == IMAGE_BACKEND_PILLOW:
            return Image.load_image_PIL(path, precision)