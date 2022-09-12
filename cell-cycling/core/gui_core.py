from dataclasses import dataclass, field
import math
import streamlit as st
from typing import List, Union, Dict

from core.experiment import Experiment
from core.exceptions import DuplicateName


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

    def empty_view(self, name: str):
        """
        Remove all the selected elements from a given view

        Arguments
        ---------
        name : str
            the name of the experiment to empty
        """
        if name in self.view:
            self.view[name] = []
        else:
            raise RuntimeError

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

    def remove_all(self):
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


@dataclass
class SingleCycleSeries:

    label: str
    experiment_name: str
    cycle_id: int
    hex_color: str = None
    color_from_base: bool = False


@dataclass
class StackedPlotSettings:

    x_axis: str = None
    y_axis: str = None
    x_autorange: bool = True
    y_autorange: bool = True
    x_range: List[float] = None
    y_range: List[float] = None
    shared_x: bool = None
    scale_by_volume: bool = False
    scale_by_area: bool = False
    show_charge: bool = True
    show_discharge: bool = True
    reverse: bool = False
    font_size: int = 14
    axis_font_size: int = 18
    plot_height: int = 500
    format: str = None
    total_width: int = None


@dataclass
class ComparisonPlotSettings:

    x_axis: str = None
    y_axis: str = None
    scale_by_volume: bool = False
    scale_by_area: bool = False
    show_charge: bool = True
    show_discharge: bool = True
    font_size: int = 14
    axis_font_size: int = 18
    reverse: bool = False
    height: int = 600
    format: str = None
    width: int = 1200


@dataclass
class CellcyclingPlotSettings:

    annotation_size: int = 14
    annotation_color: str = "#000000"
    primary_axis_name: str = None
    secondary_axis_name: str = None
    y_axis_mode: str = None
    scale_by_volume: bool = False
    scale_by_area: bool = False
    primary_axis_marker: str = None
    secondary_axis_marker: str = None
    marker_size: str = 8
    marker_with_border: str = False
    which_grid: str = None
    font_size: str = 14
    axis_font_size: int = 18
    height: str = 600
    format: str = None
    width: str = 1200
    limits: dict = field(
        default_factory=lambda: {
            "x": [None, None],
            "y": [None, None],
            "y2": [None, None],
            "y_annotation_reference": [None, None],
        }
    )
    annotations: dict = field(default_factory=lambda: {})
