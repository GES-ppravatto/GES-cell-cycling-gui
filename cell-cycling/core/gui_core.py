from __future__ import annotations
from dataclasses import dataclass
import math
import streamlit as st
from io import BytesIO
from os.path import splitext
from typing import List, Tuple, Union, Dict, Any
from palettable.cartocolors.qualitative import Prism_8
from palettable.cartocolors.cartocolorspalette import CartoColorsMap
from colorsys import rgb_to_hsv, rgb_to_hls, hsv_to_rgb, hls_to_rgb

from echemsuite.cellcycling.read_input import FileManager, Instrument
from echemsuite.cellcycling.cycles import Cycle

# %% Define functions to operate on colors


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

# Counter of the number of calls to the Experiment.__init__ function
_EXPERIMENT_INIT_COUNTER_: int = 0


class Experiment:
    """
    Class devoted to describe an experiment and its properties in the GUI.

    Arguments
    ---------
        uploaded_files :  list
            list of streamlit UploadedFile objects to be used in the construction of the
            experiment

    Attributes
    ----------
        _manager : FileManager
            file manager object containing all the loaded experiment properties and all the
            quantitative tools to be called during the experiment manipulation
        _ordering : List[List[str]]
            list of lists of filenames representing the ordering of the input files in the
            construction of the halfcycles
        _clean : bool
            flag setting the non-physical cycle cleaning option
        _id : int
            univocal key identifying the experiment object
        _name : str
            name of the experiment to be shown to the user
        _base_color : ColorRGB
            base color associated to the experiment to be used as basecolor in the process
            of plotting graphs
        _volume : float
            volume in liters associated to the experiment. Useful in the computation of
            volumetrical properties
        _skipped_files : int
            counter of the number of files skipped during the parsing process

    """

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
            original = BytesIO(file.getvalue())
            decoded = original.read().decode("utf-8", errors="ignore")
            unicode_text = "".join([char for char in decoded if ord(char) < 128])
            bytestreams[file.name] = BytesIO(unicode_text.encode("utf-8"))

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
        self._skipped_files = 0

    def __iadd__(self, source: Experiment):
        """
        Method used to add a new experiment to the current one using the += operator
        """
        # Verify that the type of the incoming object is the correct one
        if type(source) != Experiment:
            raise TypeError

        # Verify that the name of the incoming experiment matches the current one
        if source.name != self.name:
            return ValueError

        # Add all the bytestream from the other experiment to the local bytestream buffer
        for key, item in source._manager._bytestreams.items():
            self._manager._bytestreams[key] = item

        # Parse the buffer to update all data
        self._manager.parse()
        return self

    def remove_file(self, filename: str) -> None:
        """
        Remove a file from the experiment given its name

        Arguments
        ---------
            filename : str
                filename of the file to remove
        """
        # Check that the required file to be removed is actually present
        if filename in self._manager.bytestreams.keys():
            del self._manager.bytestreams[filename]
            self._manager.parse()
            self._ordering = self._manager.suggest_ordering()
        else:
            raise ValueError

    def append_file(
        self, filename: str, bytestream: BytesIO, autoparse: bool = True
    ) -> None:
        """
        Add a new file to the experiment

        Arguments
        ---------
            filename : str
                filename of the new file to add
            bytestream : BytesIO
                content of the file in the form of a BytesIO stream
            autoparse : bool
                if set to True (default) call the parse function after the append call
        """
        # Append the bytestream to the corresponding buffer
        self._manager.bytestreams[filename] = bytestream
        if autoparse:
            self._manager.parse()

    @property
    def name(self) -> str:
        """
        getter of the name of the experiment
        """
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        """
        setter of the name of the experiment
        """
        if type(value) != str or value == "":
            raise ValueError
        self._name = value

    @property
    def volume(self) -> float:
        """
        getter of the volume associated to the experiment
        """
        return self._volume

    @volume.setter
    def volume(self, value: float) -> None:
        """
        setter of the volume associated to the experiment
        """
        if type(value) != float or value <= 0:
            raise ValueError
        self._volume = value

    @property
    def color(self) -> ColorRGB:
        """
        getter of the color associated to the experiment
        """
        return self._base_color

    @color.setter
    def color(self, color: ColorRGB) -> None:
        """
        setter of the color associated to the experiment
        """
        self._base_color = color

    @property
    def manager(self) -> FileManager:
        """
        getter of the file manager object
        """
        return self._manager

    @property
    def ordering(self) -> List[List[str]]:
        """
        getter of the ordering list
        """
        return self._ordering

    @ordering.setter
    def ordering(self, new_ordering: List[List[str]]) -> None:
        """
        setter of the ordering list
        """

        # generate a list containing all the files in the ordering list
        filelist = []
        for level in new_ordering:
            for name in level:
                filelist.append(name)

        # verify that all the files in the current halfcycle buffer matches the one loaded
        for key in self._manager._halfcycles.keys():
            if key not in filelist:
                print(f"The file {key} is missing from the new ordering")
                raise RuntimeError

        # verify that all the files in the given list match the one in the halfcycle buffer
        for name in filelist:
            if name not in self._manager._halfcycles.keys():
                raise RuntimeError

        # save the given ordering
        self._ordering = new_ordering

    @property
    def clean(self):
        """
        getter of the clean variable
        """
        return self._clean

    @clean.setter
    def clean(self, value: bool):
        """
        setter of the clean variable
        """
        if type(value) != bool:
            raise TypeError
        self._clean = value

    @property
    def cycles(self) -> List[Cycle]:
        """
        getter of the cycles with automatic call to parse
        """
        self._manager.parse()
        return self._manager.get_cycles(self._ordering, self._clean)


# %% Define the ProgramStatus class to univocally identify the status of the GUI


class ProgramStatus:
    """
    Service class used to moitor and save the relevant parameters of the GUI execution.

    Attributes
    ----------
        _experiments : List[Experiment]
            list of all the loaded experiments
    """

    def __init__(self) -> None:
        # Set the experiment list as empty by default
        self._experiments: List[Experiment] = []

    def __getitem__(self, index: int) -> Experiment:
        """
        Returns the experiment corresponding to a given index
        """
        if index >= len(self._experiments) or index < 0:
            raise ValueError
        return self._experiments[index]

    def __setitem__(self, index: int, value: Experiment) -> None:
        """
        Set the experiment corresponding to a given index
        """
        if index >= len(self._experiments) or index < 0:
            raise ValueError
        if type(value) != Experiment:
            raise TypeError
        self._experiments[index] = value

    def __iter__(self) -> Experiment:
        """
        Iterator yielding all the experiments in the buffer
        """
        for experiment in self._experiments:
            yield experiment

    def __len__(self) -> int:
        """
        Length of the experiment buffer
        """
        return len(self._experiments)

    def get_experiment_names(self) -> List[str]:
        """
        Retruns a list of the experiment names

        Returns
        -------
            List[str]
                list of strings representing the name of each experiment in the buffer
        """
        return [obj.name for obj in self._experiments]

    def get_index_of(self, name: str) -> int:
        """
        Returns the index of the experiment marked with a given name

        Arguments
        ---------
            name : str
                the name of the selected experiment

        Returns
        -------
            int
                the index of the experiment in the experiment buffer
        """
        return self.get_experiment_names().index(name)

    def append_experiment(self, experiment: Experiment) -> None:
        """
        Append a new experiment object to the experiment buffer

        Arguments
        ---------
            experiment : Experiment
                the experiment to be added to the experiment list
        """

        # Check that the incomig object matches the type Experiment
        if type(experiment) != Experiment:
            raise TypeError

        # Check if the name of the incoming experiment is already present in the buffer, if
        # yes raise an error in order to avoid un-univocal experiment names assigment
        if experiment.name in self.get_experiment_names():
            raise DuplicateName

        self._experiments.append(experiment)

    def remove_experiment(self, index: int):
        """
        Remove an experiment given its index

        Arguments
        ---------
            index : int
                index of the experiment to remove
        """
        if index >= len(self._experiments) or index < 0:
            raise ValueError
        del self._experiments[index]

    @property
    def number_of_experiments(self):
        """
        Numeber of experiments in the class
        """
        return len(self._experiments)


# %% DEFINE EXPERIMENT SELECTOR


class CycleFormat:
    def __init__(self, number, label=None) -> None:
        self.number = number
        if label is not None:
            self.label = label
        else:
            self.set_default_label()
    
    def set_default_label(self) -> None:
        self.label = f"Cycle {self.number}"


class ExperimentSelector:
    """
    Service class used to select a set of experiment to be analyzed and specify for each of
    them a subset of cycles to be exaimend.

    Attributes
    ----------
        view : Dict[str, List[CycleFormat]]
            dictionary containing the name of the experiment and the list of cycle properties
    """

    def __init__(self) -> None:
        self.view: Dict[
            str, List[CycleFormat]
        ] = {}  # set the dictionary as initially empty

    def __getitem__(self, name: str) -> List[int]:
        """
        returns the cycle list correspondent to a given experiment
        """
        # return the cycle view for the experiment if existent else raise an exception
        if name in self.view:
            cycle_ids = [obj.number for obj in self.view[name]]
            return cycle_ids
        else:
            raise ValueError

    def __len__(self):
        """
        Return the len of the ExperimentSelector as the number of views existent
        """
        return len(self.view)

    def set(
        self,
        name: str,
        cycles: Union[List[int], None] = None,
        labels: Union[List[str], None] = None,
    ) -> None:
        """
        Set a new experiment either by specifying a cycle list or by default.

        Arguments
        ---------
            name : str
                the name of the experiment
            cycles : Union[List[int], None]
                if set to None will automatially trigger the inclusion of all the cycles
                available in the experiment. If equal to a list of integers, set the cycles
                list to the given one.
            labels : Union[List[str], None]
                if set to None will automatically provide a list of default labels. If equal
                to a list of stings, sets the label associated to each series.
        """

        # Fetch from the GUI session state variable the ProgramStatus object
        status: ProgramStatus = st.session_state["ProgramStatus"]

        # Chech if the name of the experiment exist in the program memory
        if name not in status.get_experiment_names():
            raise ValueError

        # Get the index of the experiment in the status memory
        id = status.get_index_of(name)

        # If cycles is None include all the available cycles in the experiment
        if cycles is None:
            cycle_list = status[id].manager.get_cycles()
            stride = int(math.ceil(len(cycle_list) / 10))
            cycles = [
                cycle.number for idx, cycle in enumerate(cycle_list) if idx % stride == 0
            ]

        # Else, check that all the given cycle index ar valid
        else:
            for number in cycles:
                if number < 0 or number >= len(status[id].manager.get_cycles()):
                    raise ValueError

        # If labels are provided check that the list length match and apply the given labels
        if labels is not None:
            if len(labels) != len(cycles):
                raise RuntimeError
            self.view[name] = [
                CycleFormat(idx, label) for idx, label in zip(cycles, labels)
            ]

        # If no labels are provided generate a default set
        else:
            
            # If the view already exist generate only the missing labels
            if name in self.view:
                current_cycles = [obj.number for obj in self.view[name]]
                current_lables = [obj.label for obj in self.view[name]]

                updated_view = []
                for idx in cycles:
                    if idx in current_cycles:
                        position = current_cycles.index(idx)
                        updated_view.append(CycleFormat(idx, current_lables[position]))
                    else:
                        updated_view.append(CycleFormat(idx))
                self.view[name] = updated_view
            
            # Else create a new default view labelling
            else:
                self.view[name] = [CycleFormat(idx) for idx in cycles]


    def remove(self, name: str):
        """
        Remove a given view from the view buffer

        Arguments
        ---------
            name : str
                the name of the experiment to remove
        """
        if name in self.view:
            del self.view[name]

    def clear(self):
        """
        Clear all the view
        """
        self.view = {}

    def set_cycle_label(self, name: str, index: int, label: str) -> None:
        """
        Sets the label associated to a given cycle

        Arguments
        ---------
            name : str
                name of the experiment to which the cycle belongs to
            index : int
                index of the target cycle (number of the cycle in the experiment)
            label : str
                the lable that must be set
        """
        if name not in self.view:
            raise ValueError

        if index not in [obj.number for obj in self.view[name]]:
            raise ValueError
        
        idx = self[name].index(index)
        self.view[name][idx].label = label
    
    def reset_default_labels(self, name: str) -> None:
        """
        Sets all the cycles lable of an experiment to the default format.

        Arguments
        ---------
            name : str
                the name of the experiment
        """
        if name not in self.view.keys():
            raise ValueError
        
        for obj in self.view[name]:
            obj.set_default_label()
    
    def get_labels(self, name: str) -> None:
        """
        Gets the list of labels associated to the selected cycles in the experiment

        Arguments
        ---------
            name : str
                name of the experiment
        """
        if name not in self.view:
            raise ValueError

        return [obj.label for obj in self.view[name]]
    
    def get_label(self, name: str, index: int) -> str:
        """
        Gets the label associated to the selected cycle

        Arguments
        ---------
            name : str
                name of the experiment to which the cycle belongs to
            index : int
                number of the cycle in the corresponding experiment
        
        Returns
        -------
            str
                label associate to the experiment
        """

        if name not in self.view:
            raise ValueError
        
        idx = self[name].index(index)
        return self.view[name][idx].label



    @property
    def names(self) -> List[str]:
        """
        getter of the list containing all the experiment names
        """
        return self.view.keys()

    @property
    def is_empty(self):
        """
        returns true if the view buffer is empty
        """
        return True if len(self) == 0 else False


# %% Define dataclass to store a general plot series attriburtes for cycle comparison plot

@dataclass
class SingleCycleSeries:
    label : str
    experiment_name : str
    cycle_id : int
    hex_color : str = None