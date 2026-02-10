from dataclasses import dataclass, field


@dataclass
class DependencyPosition:
  """Represents an Entities position in the a dependency hierarchy, whose members belong to a containing class entity. (e.g. Installation -> Facilities)

  A Position format: "{vertical_position}{group_ids}" e.g. "A1" or "B12"
    - vertical_position can be any letter "A-Z"
    - and group_ids can be any combination of the integers 1-9, each representing membership to 1 of 9 possible groups. 
  """

  vertical_position: str  # single characters (e.g., "A"-"Z")
  group_ids: list[int] = field(default_factory=list) #






