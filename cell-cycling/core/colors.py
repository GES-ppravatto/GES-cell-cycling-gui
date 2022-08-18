import plotly
from typing import Tuple, Union
from palettable.cartocolors.cartocolorspalette import CartoColorsMap
from colorsys import rgb_to_hsv, rgb_to_hls, hsv_to_rgb, hls_to_rgb


class ColorRGB:
    """
    Color class to handle RGB colors encoded in 3 channels with a resolution of 8-bits

    Arguments
    ---------
        r : int
            the value associated to the red channel
        g : int
            the value associated to the green channel
        b : int
            the value associated to the blue channel
    """

    def __init__(self, r: int, g: int, b: int) -> None:

        for c in [r, g, b]:
            if type(c) != int:
                raise TypeError
            if c < 0 or c > 255:
                raise ValueError

        self.r, self.g, self.b = r, g, b

    def get_RGB(self):
        """
        Returns the RGB values stored in the object

        Returns
        -------
            Tuple[int, int, int]
                The values associated to the red, green and blue channels respectively
        """
        return self.r, self.g, self.b

    def saturate(self, replace: bool = False) -> Union[Tuple[int, int, int], None]:
        """
        Function used to set a 100% saturation to the stored color.

        Arguments
        ---------
            replace : bool
                if set to True will override the content of the class returning nothing,
                if set to False will leave the object unchanged returning the new RGB values

        Returns:
            Union[Tuple[int, int, int], None]
                either the saturated red, green and blue values if replace in set to False,
                None if replace is set to True
        """
        h, _, v = rgb_to_hsv(self.r / 255.0, self.g / 255.0, self.b / 255.0)
        r, g, b = [int(255.0 * c) for c in hsv_to_rgb(h, 1.0, v)]
        if replace:
            self.r, self.g, self.b = r, g, b
        else:
            return r, g, b

    def get_shade(self, index, levels, reversed=True):
        """
        Generates a shade of the saturated color saved in the object based on an integer
        index and a number of levels.

        Arguments
        ---------
            index : int
                the index of the shade to generate
            levels : int
                the number of shade levels expected
            reversed : bool
                if set to True the color will be lighter the higher the value of index else
                the color will be darker for higher values of index
        """
        if index >= levels:
            raise ValueError

        r, g, b = self.saturate()
        h, _, s = rgb_to_hls(r / 255.0, g / 255.0, b / 255.0)

        # Set the maximum or the color luminance to 0.9 and the minimum to 0.3 to avoid full
        # black or full white color shades
        if reversed:
            l = 0.3 + 0.6 * (index / (levels + 1))
        else:
            l = 0.9 - 0.6 * (index / (levels + 1))

        r, g, b = [int(255 * c) for c in hls_to_rgb(h, l, s)]
        return r, g, b


def get_basecolor(palette: CartoColorsMap, index: int) -> ColorRGB:
    """
    Function to obtain the ColorRGB object associated to a given index of a palette

    Arguments
    ---------
        palette : CartoColorsMap
            the selected palette
        index : int
            the index of the color in the palette, if the index is grater than the palette
            length the color-sequence will automatically loop around to the first color.

    Returns
    -------
        ColorRGB
            the RGB color object correspondent to the selected palette shade
    """
    color = palette.colors[index % palette.number]
    return ColorRGB(color[0], color[1], color[2])


def RGB_to_HEX(r: int, g: int, b: int) -> str:
    """
    Returns the HEX representation of a given RGB color

    Arguments
    ---------
        r : int
            the value associated to the red channel
        g : int
            the value associated to the green channel
        b : int
            the value associated to the blue channel

    Returns
    -------
        str
            the string, starting with #, containing the hexadecimal representation of the
            rgb color
    """
    return "#%02x%02x%02x" % (r, g, b)


def HEX_to_RGB(value: str) -> Tuple[int, int, int]:
    """
    Returns the tuple of integer RGB values associated to a given HEX sting

    Arguments
    ---------
        value : str
            the hexadecimal color string starting with #

    Returns
    -------
        Tuple[int, int, int]
            the tuple of RGB colors encoded by the string
    """
    value = value.lstrip("#")
    lv = len(value)
    return tuple(int(value[i : i + lv // 3], 16) for i in range(0, lv, lv // 3))


def get_plotly_color(index: int) -> str:
    color_list = plotly.colors.qualitative.Plotly
    return color_list[index % len(color_list)]

