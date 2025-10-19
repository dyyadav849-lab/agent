from enum import Enum


class TextSplitterEnum(Enum):
    """
    Source of truth for text splitter, add for every new text splitter
    """

    DEFAULT = 0
    RECURSIVE = 1

    def __str__(self) -> str:
        return self.name


text_splitter_mapper = {
    0: TextSplitterEnum.DEFAULT.name,
    1: TextSplitterEnum.DEFAULT.name,
}
