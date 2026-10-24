"""Discovery of Mraya update packages.

An update package is a pip-installable Django app. It is picked up from either:
  * the ``mraya.plugins`` entry-point group, e.g. in its pyproject.toml:
        [project.entry-points."mraya.plugins"]
        goals = "mraya_goals"
  * the comma-separated ``MRAYA_PLUGINS`` environment variable.

If the app has a ``urls`` module, it is mounted at ``/ext/<label>/``.
"""
import logging
from importlib import import_module
from importlib.metadata import entry_points

logger = logging.getLogger("apps.plugins")


def discover_plugins(env_value=""):
    found = []
    for ep in entry_points(group="mraya.plugins"):
        found.append(ep.value)
    found.extend(name.strip() for name in env_value.split(",") if name.strip())

    plugins = []
    for module_path in dict.fromkeys(found):  # de-duplicate, keep order
        try:
            import_module(module_path)
        except ImportError:
            logger.warning("Mraya plugin %r is not importable; skipping", module_path)
            continue
        plugins.append(module_path)
    return plugins


def plugin_urlpatterns(plugin_apps):
    from django.urls import include, path

    patterns = []
    for module_path in plugin_apps:
        try:
            import_module(f"{module_path}.urls")
        except ImportError:
            continue
        label = module_path.rsplit(".", 1)[-1]
        patterns.append(path(f"ext/{label}/", include(f"{module_path}.urls")))
    return patterns
