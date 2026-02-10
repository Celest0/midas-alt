from enum import Enum


class UFCGrade(Enum):
    """As Defined By: UFC 4-141-03: https://www.wbdg.org/FFC/DOD/UFC/ufc_4_141_03_2024.pdf.

    Enumerates the resiliency grading system for facilities based on redundancy,
    maintainability, and fault-tolerance as defined in DoD and industry standards.

    - G1: No redundant capacity components or redundant distribution pathways.
          Maintenance or failures result in downtime. Comparable to Uptime Institute's
          Tier I, ANSI/TIA-942-B I, ANSI/BICSI 002 Class F1.
    - G2: Single paths to critical loads with some component redundancy
          (but not system-level redundancy). Planned maintenance only possible
          for redundant components. Downtime likely for failures. Comparable to
          Tier II, ANSI/TIA-942-B II, ANSI/BICSI 002 Class F2.
    - G3: Concurrently maintainable, redundant components for critical operations.
          Operations sustained for any scheduled maintenance routine. Systems
          typically N+1 at minimum. Comparable to Tier III, ANSI/TIA-942-B III,
          ANSI/BICSI 002 Class F3.
    - G4: Fault-tolerant facilities with physically isolated redundant paths for
          all critical operations and automatic fault response. Can withstand a
          single failure during operation, but may lose operation if failure occurs
          during maintenance. Systems are 2N or higher. Comparable to Tier IV,
          ANSI/TIA-942-B IV, ANSI/BICSI 002 Class F4.
    """

    G1 = "1"
    """Not applicable to C5ISR facilities. A facility that has no redundant capacity components and no redundant distribution pathways. Maintenance or failures result in facility down time. For cross reference, this Grade 1 definition is a DoD specific definition that is similar in scope to Uptime Institute’s Tier I Data Center, ANSI/TIA-942-B I Data Center, and ANSI/BICSI 002 Class F1."""

    G2 = "2"
    """A facility that contains single path(s) to critical loads while having some component redundancy. Component redundancy includes added equipment to exceed N requirements but not system level redundancy. This type of system would be vulnerable to component level faults with no added path around failures. It is possible to have planned component level maintenance but only on those components with the added redundancy. In most cases, maintenance or failures would cause downtime to the critical loads supporting the mission. For cross reference, this Grade 2 definition is a DoD specific definition that is similar in scope to Uptime Institute’s Tier II  Data Center Topology, ANSI/TIA-942-B II Data Center, and ANSI/BICSI 002 Class F2."""

    G3 = "3"
    """A concurrently maintainable facility with redundant components to service critical operations. The facility must maintain operations for any scheduled maintenance routine without loss in availability. Major features of these facilities include mechanical and electrical systems with N+1 design architectures at a minimum. These architectures may be 50 percent higher in cost compared to a similar-sized facility with no redundancy. For cross reference, this Grade 3 definition is a DoD specific definition that is similar in scope to Uptime Institute’s Tier III Data Center Topology, ANSI/TIA-942-B III Data Center, and ANSI/BICSI 002 Class F3."""

    G4 = "4"
    """A fault-tolerant facility with independent systems that provide redundant paths to critical operations of the facility and automatic response to faults. Equipment associated with redundant paths are physically isolated to prevent catastrophic events from impacting the operations. This facility can maintain availability during a single component, system, or infrastructure failure by initiating an automatic sequence of operations. It may suffer from loss of operations if a component fails during a scheduled maintenance event. Major features of these facilities include mechanical and electrical systems with 2N design architectures at a minimum. These architectures may cost 100-300 percent more than a similar-sized facility with no redundancy. Cost will increase significantly with additional full capacity (N) redundant paths. For cross reference, this Grade 4 definition is a DoD specific definition that is similar in scope to Uptime Institute’s Tier IV Data Center Topology, ANSI/TIA-942-B IV Data Center, and ANSI/BICSI 002 Class F4."""

    @classmethod
    def from_value(cls, value: int | str) -> "UFCGrade | None":
        """Get grade from integer or string value."""
        try:
            int_val = int(value)
            return cls(int_val)
        except (ValueError, TypeError):
            return None
