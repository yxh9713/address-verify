from abc import ABC, abstractmethod

from entities.address import Address

# 1. Define the abstract base class (blueprint)
class AddressValidator(ABC):
    @abstractmethod
    def validate(self, address: Address) -> Address:
        pass
