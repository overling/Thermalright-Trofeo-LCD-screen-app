"""Platform implementations — one module per OS, dispatched by PlatformFactory.

The factory IS the OCP chokepoint for OS support: a new OS adds one
file under ``adapters/system/`` with ``@PlatformFactory.register("haiku")``
on its ``Platform`` subclass.  Importing this package fires the
side-effect import of every OS file, which fires their ``@register``
decorators, which populates the registry.

``core/ports.Platform`` stays a pure ABC — no ``_BY_OS`` dispatch
table, no ``importlib.import_module`` from core, no DIP inversion.

See ``memory/project_hexagonal_solid_dry_plan`` §2.
"""

from __future__ import annotations

import logging
import sys
from collections.abc import Callable
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from ...core.ports import Platform

log = logging.getLogger(__name__)


class PlatformFactory:
    """Registry + dispatch chokepoint for OS-specific ``Platform`` subclasses.

    Subclasses self-register via ``@PlatformFactory.register("win32")``
    (etc.); ``current()`` returns a fresh instance of the registration
    matching ``sys.platform``.  Unknown platforms fall back to Windows
    with a warning.
    """

    _REGISTRY: ClassVar[dict[str, type[Platform]]] = {}

    @classmethod
    def register(cls, key: str) -> Callable[[type[Platform]], type[Platform]]:
        """Decorator: register *platform_cls* under *key* (a sys.platform name)."""
        def deco(platform_cls: type[Platform]) -> type[Platform]:
            cls._REGISTRY[key] = platform_cls
            log.debug("PlatformFactory: registered %s for %s",
                      platform_cls.__name__, key)
            return platform_cls
        return deco

    @classmethod
    def current(cls) -> Platform:
        """Construct a fresh ``Platform`` for the running OS."""
        key = sys.platform
        if "bsd" in key:
            key = "bsd"
        if key not in cls._REGISTRY:
            log.warning(
                "PlatformFactory.current: %s not registered, falling back "
                "to windows", key,
            )
            key = "win32"
        log.info("PlatformFactory.current: building %s", cls._REGISTRY[key].__name__)
        return cls._REGISTRY[key]()


# Side-effect imports: load each OS module so its @register decorator
# fires and populates the registry above.
from . import windows as _windows  # noqa: E402, F401
