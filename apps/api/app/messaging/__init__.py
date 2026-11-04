"""Messaging provider abstraction and worker services.

No module in this package contacts a live provider at import time. The default
provider is ``fake`` and every safety switch defaults to disabled.
"""

from .types import ProviderResult

__all__ = ["ProviderResult"]
