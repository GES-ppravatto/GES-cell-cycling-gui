from __future__ import annotations
import streamlit as st
from io import BytesIO
from os.path import splitext
from typing import List, Tuple
from palettable.cartocolors.qualitative import Prism_8

from core.colors import get_basecolor, ColorRGB
from core.exceptions import MultipleExtensions, UnknownExtension
from echemsuite.cellcycling.read_input import FileManager, Instrument
from echemsuite.cellcycling.cycles import Cycle, CellCycling


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
        _area : float
            area in squared centimeters associated to the experiment. Useful in the 
            computation of surface related properties
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
            raise MultipleExtensions(extensions)

        if extensions[0].lower() == ".dta":
            self._manager._instrument = Instrument.GAMRY
        elif extensions[0].lower() == ".mpt":
            self._manager._instrument = Instrument.BIOLOGIC
        else:
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
        self._manual_hide = []

        # Create a buffer for the cycle based objects
        self._cycles = None
        self._cellcycling = None
        self._update_cycles_based_objects()

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
        self._area = None  # Volume of the electrolite in liters
        self._skipped_files = 0

    def _update_cycles_based_objects(self) -> None:
        self._cycles = self._manager.get_cycles(self._ordering, self._clean)
        self._cellcycling = CellCycling(self._cycles)
        self._cellcycling.hide(self._manual_hide)

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
        self._update_cycles_based_objects()
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
            self._update_cycles_based_objects()
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
            self._update_cycles_based_objects()

    def hide_cycle(self, index: int) -> None:
        self._manual_hide.append(index)
        self._update_cycles_based_objects()

    def unhide_all_cycles(self) -> None:
        self._manual_hide = []
        self._update_cycles_based_objects()

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
    def area(self) -> float:
        """
        getter of the area associated to the experiment
        """
        return self._area

    @area.setter
    def area(self, value: float) -> None:
        """
        setter of the area associated to the experiment
        """
        if type(value) != float or value <= 0:
            raise ValueError
        self._area = value

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
        self._update_cycles_based_objects()

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
        self._update_cycles_based_objects()

    @property
    def cycles(self) -> List[Cycle]:
        """
        getter of the cycles list
        """
        return self._cycles

    @property
    def cellcycling(self) -> CellCycling:
        """
        getter of the cellcycling object
        """
        return self._cellcycling


# Define an Experiment container to hold all the experiments related to a single multi-parameter
# cycling experiment
class ExperimentContainer:
    def __init__(self, name: str, color: str = None) -> None:
        self._name = name
        self._color = color if color is not None else "#000000"
        self._experiments: List[Experiment] = []

    def __iter__(self) -> Tuple[str, CellCycling]:
        for experiment in self._experiments:
            yield experiment.name, experiment.cellcycling

    @property
    def name(self) -> str:
        return self._name

    @property
    def get_experiment_names(self) -> List[str]:
        return [name for name, _ in self]

    @property
    def hex_color(self) -> str:
        return self._color

    @property
    def max_cycles_numbers(self) -> List[int]:
        numbers = []
        for _, obj in self:
            obj.get_numbers()
            numbers.append(obj._numbers[-1])
        return numbers

    def add_experiment(self, experiment: Experiment) -> None:
        if experiment not in self._experiments:
            self._experiments.append(experiment)
        else:
            raise RuntimeError

    def remove_experiment(self, name: str) -> None:
        if name in [obj.name for obj in self._experiments]:
            id = [obj.name for obj in self._experiments].index(name)
            del self._experiments[id]
        else:
            raise ValueError

    def clear_experiments(self) -> None:
        self._experiments = {}

    def hide_cycle(self, cumulative_id: int) -> None:
        cumulative_sum = []
        for i, number in enumerate(self.max_cycles_numbers):
            cumulative_sum.append(number if i == 0 else cumulative_sum[-1] + number + 1)

        experiment_id, cycle_id = None, None
        for i, threshold in enumerate(cumulative_sum):
            if cumulative_id <= threshold:
                experiment_id = i
                if i == 0:
                    cycle_id = cumulative_id
                else:
                    cycle_id = cumulative_id - cumulative_sum[i - 1] - 1
                break

        self._experiments[experiment_id].hide_cycle(cycle_id)