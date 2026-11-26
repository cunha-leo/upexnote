"""Edition policy shared by source and frozen worker."""
import os
import sys

if getattr(sys, "frozen", False):
    from ._build_edition import INTERNAL
else:
    INTERNAL = os.environ.get("UPEXNOTE_EDITION") == "internal"
