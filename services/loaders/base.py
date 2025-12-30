from abc import ABC, abstractmethod
from typing import Iterable, Tuple

class BaseLoader(ABC):
    file_type: str

    @abstractmethod
    def load(self, file_path: str) -> Iterable[Tuple[int, str]]:
        """
        반환:
        [
          (unit_no, text),
          ...
        ]
        """
        pass
