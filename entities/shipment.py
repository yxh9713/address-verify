from dataclasses import dataclass
from entities.address import Address

@dataclass
class Shipment:
    raw_id: int
    address: Address
