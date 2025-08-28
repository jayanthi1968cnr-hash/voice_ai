from .registry import SKILLS, register
# auto-import core skills
from . import core_time, core_memory  # noqa: F401
