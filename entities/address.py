from dataclasses import dataclass
from typing import Optional

@dataclass
class Address:
    address_one: str = ""
    address_two: Optional[str] = None
    city: str = ""
    state: str = ""
    zip: str = ""
    longitude: Optional[float] = None
    latitude: Optional[float] = None
    timezone: Optional[str] = None
    residential: Optional[str] = None # BUSINESS, RESIDENCE
    id: Optional[int] = None

    valid: bool = False

    # def __str__(self) -> str:
    #     return (
    #         f"Address{{"
    #         f"addressOne='{self.address_one}', "
    #         f"addressTwo='{self.address_two}', "
    #         f"city='{self.city}', "
    #         f"state='{self.state}', "
    #         f"zip='{self.zip}'"
    #         f"}}"
    #     )

    def check_required_fields(self) -> bool:
        return bool(self.address_one and self.city and self.state and self.zip)