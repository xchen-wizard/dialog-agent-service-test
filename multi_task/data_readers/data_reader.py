from __future__ import annotations

from abc import ABC
from abc import abstractmethod


class DataReader(ABC):

    @abstractmethod
    def sample(self, n):
        """
        :param n: number of samples needed
        :return: tuple of input encoding: List[Tensor], label encoding: List[Tensor]
        """
        raise RuntimeError('Sample not implemented for the data reader')
