from typing import List

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