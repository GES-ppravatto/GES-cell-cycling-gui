import streamlit as st
from io import BytesIO
from os.path import splitext
from typing import List, Tuple, Union
from palettable.cartocolors.qualitative import Prism_8
from palettable.cartocolors.cartocolorspalette import CartoColorsMap
from colorsys import rgb_to_hsv, hsv_to_rgb

from echemsuite.cellcycling.read_input import FileManager, Instrument
from echemsuite.cellcycling.cycles import Cycle


# %% Define functions to operate on colors


class ColorRGB:
    def __init__(self, r: int, g: int, b: int) -> None:

        for c in [r, g, b]:
            if type(c) != int:
                raise TypeError
            if c < 0 or c > 255:
                raise ValueError

        self.r, self.g, self.b = r, g, b

    def get_RGB(self):
        return self.r, self.g, self.b

    def saturate(self, replace: bool = False) -> Union[Tuple[int, int, int], None]:
        h, _, v = rgb_to_hsv(self.r, self.g, self.b)
        r, g, b = hsv_to_rgb(h, 1, v)
        if replace:
            self.r, self.g, self.b = r, g, b
        else:
            return r, g, b

    def get_shade(self, index, levels):

        if index >= levels:
            raise ValueError

        r, g, b = self.saturate()
        h, _, v = rgb_to_hsv(r, g, b)
        s = index / (levels - 1)
        return hsv_to_rgb(h, s, v)


def get_basecolor(palette: CartoColorsMap, index: int) -> ColorRGB:
    color = palette.colors[index % palette.number]
    return ColorRGB(color[0], color[1], color[2])


def RGB_to_HEX(r: int, g: int, b: int) -> str:
    return "#%02x%02x%02x" % (r, g, b)


def HEX_to_RGB(value: str) -> Tuple[int, int, int]:
    value = value.lstrip("#")
    lv = len(value)
    return tuple(int(value[i : i + lv // 3], 16) for i in range(0, lv, lv // 3))


# %% Define custom exceptions
class MultipleExtensions(Exception):
    """
    Exception rised when more than one type of file has been submitted during upload

        Attributes:
        -----------
            extensions : List[str]
                list of all the input file extensions
    """

    def __init__(self, extensions: List[str], *args: object) -> None:
        super().__init__(*args)
        self.univocal_extensions = list(set(extensions))

    def __str__(self) -> str:
        return """Multiple extension types have been found: '{}'""".format(
            ", ".join(self.univocal_extensions)
        )


class UnknownExtension(Exception):
    """
    Exception rised when the extension of the file does not match any known format

        Attributes:
        -----------
            extension : str
                the unknown file extension
    """

    def __init__(self, extension: str, *args: object) -> None:
        super().__init__(*args)
        self.extension = extension

    def __str__(self) -> str:
        return f"""The extension '{self.extension}' does not match any known standard."""


class DuplicateName(Exception):
    """
    Exception rised when the name given to an experiment is already present in the experiment list.

        Attributes:
        -----------
            name : str
                the repreated name
    """

    def __init__(self, name: str, *args: object) -> None:
        super().__init__(*args)
        self.name = name

    def __str__(self) -> str:
        return f"""The experiment name '{self.name}' is already used."""


# %% Define experiment class to store the experiment data and user configuration

_EXPERIMENT_INIT_COUNTER_: int = (
    0  # Counter of the number of calls to the Experiment.__init__ function
)


class Experiment:
    def __init__(self, uploaded_files: list) -> None:

        # Initialize FileManager class object
        self._manager = FileManager(verbose=False)

        # Determine the extension of the uploaded files
        extensions = [splitext(file.name)[1] for file in uploaded_files]

        # Check if all the extension match and determine the type of instrument
        if extensions.count(extensions[0]) != len(extensions):
            st.error("ERROR: Cannot operate on different file types.")
            raise MultipleExtensions(extensions)

        if extensions[0].lower() == ".dta":
            self._manager._instrument = Instrument.GAMRY
        elif extensions[0].lower() == ".mpt":
            self._manager._instrument = Instrument.BIOLOGIC
        else:
            st.error("ERROR: Unknown file extension detected.")
            raise UnknownExtension(extensions[0])

        # Load the files in the BytesIO stream buffer of the internal FileManager class
        bytestreams = {}
        for file in uploaded_files:
            stream = BytesIO(file.getvalue())
            try:
                stream.read().decode("utf-8")
            except:
                pass
            else:
                stream.seek(0)
                bytestreams[file.name] = stream

        self._manager.bytestreams = bytestreams
        self._manager.parse()

        # Set the file ordering according to the one suggested by the FileManager
        self._ordering = self._manager.suggest_ordering()

        # Set the clean flag of the file manager to false
        self._clean = False

        # Get univocal ID based on the number of object constructed
        global _EXPERIMENT_INIT_COUNTER_
        self._id = _EXPERIMENT_INIT_COUNTER_
        _EXPERIMENT_INIT_COUNTER_ += 1

        # Set the name of the experiment by default
        self._name = f"experiment_{self._id}"

        # Set the base color to be used in the plots based on the Prism_8 palette
        self._base_color = get_basecolor(Prism_8, self._id)

        # Set other class values
        self._volume = None  # Volume of the electrolite in liters

    def __iadd__(self, source):
        if type(source) != Experiment:
            raise TypeError
        if source.name != self.name:
            return ValueError
        for key, item in source._manager._bytestreams.items():
            self._manager._bytestreams[key] = item
        return self

    def remove_file(self, filename: str) -> None:
        if filename in self._manager.bytestreams.keys():
            del self._manager.bytestreams[filename]
            self._manager.parse()
            self._ordering = self._manager.suggest_ordering()
        else:
            raise ValueError

    def append_file(
        self, filename: str, bytestream: BytesIO, autoparse: bool = True
    ) -> None:
        self._manager.bytestreams[filename] = bytestream
        if autoparse:
            self._manager.parse()

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        if type(value) != str or value == "":
            raise ValueError
        self._name = value

    @property
    def volume(self) -> float:
        return self._volume

    @volume.setter
    def volume(self, value: float) -> None:
        if type(value) != float or value <= 0:
            raise ValueError
        self._volume = value

    @property
    def color(self) -> ColorRGB:
        return self._base_color

    @color.setter
    def color(self, color: ColorRGB) -> None:
        self._base_color = color

    @property
    def manager(self):
        return self._manager

    @property
    def ordering(self) -> List[List[str]]:
        return self._ordering

    @ordering.setter
    def ordering(self, new_ordering: List[List[str]]) -> None:

        filelist = []
        for level in new_ordering:
            for name in level:
                filelist.append(name)

        for key in self._manager._halfcycles.keys():
            if key not in filelist:
                print(f"The file {key} is missing from the new ordering")
                raise RuntimeError

        for name in filelist:
            if name not in self._manager._halfcycles.keys():
                raise RuntimeError

        self._ordering = new_ordering

    @property
    def clean(self):
        return self._clean
    
    @clean.setter
    def clean(self, value: bool):
        if type(value) != bool:
            raise TypeError
        self._clean = value
    
    @property
    def cycles(self) -> List[Cycle]:
        self._manager.parse()
        return self._manager.get_cycles(self._ordering, self._clean)


# %% Define the ProgramStatus class to univocally identify the status of the GUI


class ProgramStatus:
    def __init__(self) -> None:
        self._experiments: List[Experiment] = []

    def __getitem__(self, index: int) -> Experiment:
        if index >= len(self._experiments) or index < 0:
            raise ValueError
        return self._experiments[index]

    def __setitem__(self, index: int, value: Experiment) -> None:
        if index >= len(self._experiments) or index < 0:
            raise ValueError
        if type(value) != Experiment:
            raise TypeError
        self._experiments[index] = value

    def __iter__(self) -> Experiment:
        for experiment in self._experiments:
            yield experiment

    def get_experiment_names(self) -> List[str]:
        return [obj.name for obj in self._experiments]

    def get_index_of(self, name: str) -> int:
        return self.get_experiment_names().index(name)

    def append_experiment(self, experiment: Experiment) -> None:
        if type(experiment) != Experiment:
            raise TypeError

        if experiment.name in self.get_experiment_names():
            raise DuplicateName

        self._experiments.append(experiment)

    def remove_experiment(self, index: int):
        if index >= len(self._experiments) or index < 0:
            raise ValueError
        del self._experiments[index]

    @property
    def number_of_experiments(self):
        return len(self._experiments)
