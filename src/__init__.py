"""DF-KPM-Family-Distribution [CRUX-MK]. Lazy-Imports."""

__version__ = "0.1.0-PHASE-1"


def __getattr__(name):
    if name == "FamilyMember":
        from .family_distribution_main import FamilyMember
        return FamilyMember
    if name == "AllocationShare":
        from .family_distribution_main import AllocationShare
        return AllocationShare
    if name == "compute_family_allocation":
        from .family_distribution_main import compute_family_allocation
        return compute_family_allocation
    raise AttributeError(f"module {__name__} has no attribute {name}")
