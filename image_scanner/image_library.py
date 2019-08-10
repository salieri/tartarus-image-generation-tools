import itertools as it, glob
import os
import json
from typing import Iterable, List
import random

from datetime import datetime

from dataclasses import field
from marshmallow_dataclass import dataclass
import marshmallow.validate

from .image_analyzer import ImageAnalyzer, ImageAnalysisResult
from config import Config

MAGIC = 'tartarus-generator.image-scan-cache'
VERSION = '0.1.0'


@dataclass
class ImageLibraryData:
    type: str = field(metadata={'validate': marshmallow.validate.Equal(MAGIC)}, default=MAGIC)
    version: str = field(default=VERSION)
    scan_date: str
    backgrounds: List[ImageAnalysisResult] = field(default_factory=lambda: [])
    sprites: List[ImageAnalysisResult] = field(default_factory=lambda: [])


class ImageLibrary:
    config: Config
    data: ImageLibraryData
    base_path: str
    file_extensions: List[str]

    def __init__(self, config: Config, base_path: str):
        self.config = config
        self.base_path = base_path
        self.file_extensions = ['*.jpg', '*.png', '*.gif']


    def scan_filenames(self) -> Iterable:
        return it.chain.from_iterable(glob.iglob(os.path.join(self.base_path, ext), recursive=True) for ext in self.file_extensions)


    def scan(self, base_path: str) -> ImageLibraryData:
        backgrounds = []
        sprites = []
        native = self.config.processor.native.size
        native_width = native.width
        native_height = native.height

        for filename in self.scan_filenames():
            ia = ImageAnalyzer(filename)

            details = ia.analyze()
            details.filename = os.path.relpath(details.filename, base_path)

            if (details.solid is True) and (details.width >= native_width) and (details.height >= native_height):
                backgrounds.append(details)
            else:
                sprites.append(details)

        self.data = ImageLibraryData.Schema.Load(
            {
                'type': MAGIC,
                'version': VERSION,
                'scan_date': str(datetime.now()),
                'backgrounds': backgrounds,
                'sprites': sprites
            }
        )

        return self.data


    def load(self, filename: str) -> ImageLibraryData:
        with open(filename, 'r') as fp:
            (data, err) = ImageLibraryData.Schema.Load(json.load(fp))

            if bool(err) is True:
                print(err)
                raise Exception(f"Invalid data in '{filename}'")

            self.data = data

            return data


    def save(self, filename: str, data: ImageLibraryData) -> None:
        with open(filename, 'w') as fp:
            json.dump(data.Schema().dump(), fp)


    def get_random_sprite(self) -> ImageAnalysisResult:
        return random.choice(self.data.sprites)


    def get_random_background(self) -> ImageAnalysisResult:
        return random.choice(self.data.backgrounds)
