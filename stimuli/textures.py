"""
pandastim/textures.py
Texture classes defined for display in ShowBase stimulus classes.

Part of pandastim package: https://github.com/mattdloring/pandastim

First defines the abstract base class, TextureBase. This defines the attributes
of the textures, but leaves `create_texture` undefined, to be implemented
in each subclass as a numpy array that looks how you want.

Component types (texture data types in panda3d):
https://www.panda3d.org/reference/python/classpanda3d_1_1core_1_1Texture.html#a81f78fc173dedefe5a049c0aa3eed2c0
"""

try:
    import cv2
except Exception as e:
    # shortcut for making circles on some textures
    print("error importing cv2", e)
try:
    import matplotlib.pyplot as plt
except Exception as e:
    # need this to view the textures
    print("error import matplotlib", e)

import math
from abc import ABC, abstractmethod

import numpy as np
from panda3d.core import Texture

from pandastim import utils


class TextureBase(ABC):
    """
    Base texture class: subclass this for specific textures
    Requires implementation of create_texture and __str__
    """

    def __init__(self, texture_size=512, texture_name="texture"):
        """
        :param texture_size: tuple size for texture
        :param texture_name: name of given texture
        """

        if not hasattr(texture_size, "__iter__"):
            texture_size = texture_size, texture_size

        self.texture_size = texture_size
        self.texture_name = texture_name
        self.texture_array = self.create_texture()

        self.texture = Texture(self.texture_name)

        # Set texture formatting (greyscale or rgb have different settings)
        if self.texture_array.ndim == 2:
            self.texture.setup2dTexture(
                self.texture_size[0],
                self.texture_size[1],
                Texture.T_unsigned_byte,
                Texture.F_luminance,
            )
            self.texture.setRamImageAs(self.texture_array, "L")
        elif self.texture_array.ndim == 3:
            self.texture.setup2dTexture(
                self.texture_size[0],
                self.texture_size[1],
                Texture.T_unsigned_byte,
                Texture.F_rgb8,
            )
            self.texture.setRamImageAs(self.texture_array, "RGB")
    @abstractmethod
    def create_texture(self) -> None:
        """
        :return: returns a numpy array of given size
        """
        return None

    @abstractmethod
    def __str__(self):
        """
        Return the string you want print(Tex) to show, and to save to file
        when saving catalog of stimuli.
        """
        pass

    def view(self):
        """
        Plot the texture using matplotlib. Useful for debugging.
        """
        plt.imshow(self.texture_array, vmin=0, vmax=255)
        if self.texture_array.ndim == 2:
            plt.set_cmap("gray")
        plt.title(self.texture_name)
        plt.show()


class BlankTex(TextureBase):
    """
    Empty Texture
    """

    def __init__(self, texture_name="blank_tex", value=0, *args, **kwargs):
        self.value = value  # 0 : black textures, 255: white textures
        super().__init__(texture_name=texture_name, *args, **kwargs)

    def create_texture(self) -> np.array:
        tex = np.ones((self.texture_size[1], self.texture_size[0])) * self.value
        return np.uint8(tex)

    def __str__(self) -> str:
        return f"{type(self).__name__} size:{self.texture_size}"


class RgbTex(TextureBase):
    """
    full-field color
    """

    def __init__(self, color=(255, 0, 0), texture_name="rgb_field", *args, **kwargs):
        self.color = color
        super().__init__(texture_name=texture_name, *args, **kwargs)

    def create_texture(self) -> np.array:
        if not (
            all([x >= 0 for x in self.color]) and all([x <= 255 for x in self.color])
        ):
            raise ValueError("rgb values must lie in [0,255]")

        rgb_texture = np.zeros(
            (self.texture_size[0], self.texture_size[1], 3), dtype=np.uint8
        )

        for n, i in enumerate(self.color):
            rgb_texture[..., n] = i

        return rgb_texture

    def __str__(self) -> str:
        return f"{type(self).__name__} size:{self.texture_size} rgb:{self.color}"


class CircleGrayTex(TextureBase):
    """
    Filled circle: grayscale on grayscale with circle_radius, centered at circle_center
    with face color fg_intensity on background bg_intensity. Center position is in pixels
    from center of image.
    """

    def __init__(
        self,
        circle_center=(0, 0),
        circle_radius=1,
        bg_intensity=0,
        fg_intensity=255,
        texture_name="gray_circle",
        *args,
        **kwargs,
    ):
        self.circle_center = circle_center#circle_center
        self.circle_radius = circle_radius
        self.bg_intensity = bg_intensity
        self.fg_intensity = fg_intensity
        super().__init__(texture_name=texture_name, *args, **kwargs)

    def create_texture(self) -> np.array:
        if self.fg_intensity > 255 or self.bg_intensity < 0:
            raise ValueError("Circle intensity must lie in [0, 255]")

        x = np.linspace(
            -self.texture_size[0] / 2, self.texture_size[0] / 2, self.texture_size[0]
        )
        y = np.linspace(
            -self.texture_size[1] / 2, self.texture_size[1] / 2, self.texture_size[1]
        )
        X, Y = np.meshgrid(x, y)

        circle_texture = self.bg_intensity * np.ones(
            (self.texture_size[0], self.texture_size[1]), dtype=np.uint8
        )
        circle_mask = (X - self.circle_center[0]) ** 2 + (Y - self.circle_center[1]) ** 2 <= self.circle_radius**2

        circle_texture[circle_mask] = self.fg_intensity
        return np.uint8(circle_texture)

    def __str__(self) -> str:
        return (
            f"{type(self).__name__} size:{self.texture_size} center:{self.circle_center} radius:{self.circle_radius} "
            f"bg:{self.bg_intensity} fg:{self.fg_intensity}"
        )


class SinGrayTex(TextureBase):
    """
    Grayscale sinusoidal grating texture.
    """

    def __init__(self, frequency=10, texture_name="sin_gray", *args, **kwargs):
        self.frequency = frequency
        super().__init__(texture_name=texture_name, *args, **kwargs)

    def create_texture(self) -> np.array:
        x = np.linspace(0, 2 * np.pi, self.texture_size[0] + 1)
        y = np.linspace(0, 2 * np.pi, self.texture_size[1] + 1)
        array, Y = np.meshgrid(x[: self.texture_size[0]], y[: self.texture_size[1]])
        return utils.sin_byte(array, freq=self.frequency)

    def __str__(self) -> str:
        return (
            f"{type(self).__name__} size:{self.texture_size} frequency:{self.frequency}"
        )


class SinRgbTex(TextureBase):
    """
    Sinusoid that goes from black to the given rgb value.
    """

    def __init__(
        self, color=(255, 0, 0), frequency=10, texture_name="sin_rgb", *args, **kwargs
    ):
        self.frequency = frequency
        self.color = color
        super().__init__(texture_name=texture_name, *args, **kwargs)

    def create_texture(self) -> np.array:
        if not (
            all([x >= 0 for x in self.color]) and all([x <= 255 for x in self.color])
        ):
            raise ValueError(
                "SinRgbTex.sin_texture_rgb(): rgb values must lie in [0,255]"
            )
        x = np.linspace(0, 2 * np.pi, self.texture_size[0] + 1)
        y = np.linspace(0, 2 * np.pi, self.texture_size[1] + 1)
        array, Y = np.meshgrid(x[: self.texture_size[0]], y[: self.texture_size[1]])
        R = np.uint8((self.color[0] / 255) * utils.sin_byte(array, freq=self.frequency))
        G = np.uint8((self.color[1] / 255) * utils.sin_byte(array, freq=self.frequency))
        B = np.uint8((self.color[2] / 255) * utils.sin_byte(array, freq=self.frequency))
        rgb_sin = np.zeros(
            (self.texture_size[1], self.texture_size[0], 3), dtype=np.uint8
        )
        rgb_sin[..., 0] = R
        rgb_sin[..., 1] = G
        rgb_sin[..., 2] = B
        return rgb_sin

    def __str__(self) -> str:
        return f"{type(self).__name__} size:{self.texture_size} frequency:{self.frequency} rgb:{self.color}"


class GratingGrayTex(TextureBase):
    """
    Grayscale 2d square wave (grating)
    """

    def __init__(
        self,
        frequency=10,
        light_value=255,
        dark_value=0,
        texture_name="grating_gray",
        *args,
        **kwargs,
    ):
        self.frequency = frequency
        self.dark_value = dark_value
        self.light_value = light_value
        super().__init__(texture_name=texture_name, *args, **kwargs)

    def create_texture(self) -> np.array:
        x = np.linspace(0, 2 * np.pi, self.texture_size[0] + 1)
        y = np.linspace(0, 2 * np.pi, self.texture_size[1] + 1)
        X, Y = np.meshgrid(x[: self.texture_size[0]], y[: self.texture_size[1]])
        tex = utils.grating_byte(X, freq=self.frequency)
        tex[tex == 0] = self.dark_value
        tex[tex == 255] = self.light_value
        return tex

    def __str__(self) -> str:
        return (
            f"{type(self).__name__} size:{self.texture_size} frequency:{self.frequency}"
        )


class GratingRgbTex(TextureBase):
    """
    Rgb 2d square wave (grating) stimulus class (goes from black to rgb val)
    """

    def __init__(
        self,
        color=(255, 0, 0),
        frequency=10,
        texture_name="grating_rgb",
        *args,
        **kwargs,
    ):
        self.frequency = frequency
        self.color = color
        super().__init__(texture_name=texture_name, *args, **kwargs)

    def create_texture(self) -> np.array:
        if not (
            all([x >= 0 for x in self.color]) and all([x <= 255 for x in self.color])
        ):
            raise ValueError(
                "SinRgbTex.sin_texture_rgb(): rgb values must lie in [0,255]"
            )
        x = np.linspace(0, 2 * np.pi, self.texture_size[0] + 1)
        y = np.linspace(0, 2 * np.pi, self.texture_size[1] + 1)
        array, Y = np.meshgrid(x[: self.texture_size[0]], y[: self.texture_size[1]])
        R = np.uint8(
            (self.color[0] / 255) * utils.grating_byte(array, freq=self.frequency)
        )
        G = np.uint8(
            (self.color[1] / 255) * utils.grating_byte(array, freq=self.frequency)
        )
        B = np.uint8(
            (self.color[2] / 255) * utils.grating_byte(array, freq=self.frequency)
        )
        rgb_grating = np.zeros(
            (self.texture_size[1], self.texture_size[0], 3), dtype=np.uint8
        )
        rgb_grating[..., 0] = R
        rgb_grating[..., 1] = G
        rgb_grating[..., 2] = B
        return rgb_grating

    def __str__(self) -> str:
        return f"{type(self).__name__} size:{self.texture_size} frequency:{self.frequency} rgb:{self.color}"


class CalibrationTriangles(TextureBase):
    """
    Filled circle: grayscale on grayscale with circle_radius, centered at circle_center
    with face color fg_intensity on background bg_intensity. Center position is in pixels
    from center of image.
    """

    def __init__(
        self,
        texture_size = (1024, 1024),
        tri_size=50,
        circle_radius=7,
        x_offset=500,
        y_offset=0,
        texture_name="circs",
        *args,
        **kwargs,
    ):
        self.tri_size = tri_size
        self.x_offset = x_offset
        self.y_offset = y_offset
        self.circle_radius = circle_radius
        super().__init__(texture_size = texture_size, texture_name =texture_name)

    def create_texture(self) -> np.array:
        self.midx = self.texture_size[0] // 2
        self.midy = self.texture_size[1] // 2
        self.pt1 = (
            int((self.midx + self.x_offset - (self.tri_size * math.sqrt(3)) // 2)),
            int((self.midy + self.y_offset + self.tri_size // 2)),
        )

        self.pt2 = (
            int((self.midx + self.x_offset + (self.tri_size * math.sqrt(3)) // 2)),
            int((self.midy + self.y_offset - self.tri_size // 2)),
        )

        self.pt3 = (
            int((self.midx + self.x_offset - (self.tri_size * math.sqrt(3)) // 2)),
            int((self.midy + self.y_offset - self.tri_size // 2)),
        )
        circle_texture = np.zeros((self.texture_size[1], self.texture_size[0]))

        [
            cv2.circle(circle_texture, i, self.circle_radius, 255, -1)
            for i in [self.pt1, self.pt2, self.pt3]
        ]
        return np.uint8(circle_texture)

    def __str__(self) -> str:
        return f"{type(self).__name__} size:{self.texture_size} center:{self.midx, self.midy} radius:{self.circle_radius}"

    def projct_coords(self) -> np.array:
        return np.array([self.pt1, self.pt2, self.pt3])


class RadialSinCube(TextureBase):
    def __init__(
        self, texture_size=(1024,1024), phase=0, period=32, texture_name="radial_sin_centering", *args, **kwargs
    ):
        self.phase = phase
        self.period = period
        super().__init__(texture_size=texture_size, texture_name=texture_name, *args, **kwargs)

    def create_texture(self) -> np.array:
        x = np.linspace(-self.period * np.pi, self.period * np.pi, self.texture_size[0])
        y = np.linspace(-self.period * np.pi, self.period * np.pi, self.texture_size[1])
        return np.round(
            (2 * np.pi / self.period)
            * np.sin(np.sqrt(x[None, :] ** 2 + y[:, None] ** 2) + self.phase)
            * 127
            + 127
        ).astype(np.uint8)

    def __str__(self) -> str:
        return f"{type(self).__name__} size:{self.texture_size} period:{self.period} phase: {self.phase}"
