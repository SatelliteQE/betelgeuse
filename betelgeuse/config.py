"""Betelgeuse configuration."""
import importlib

from betelgeuse import default_config


class ConfigModuleError(Exception):
    """Indicate issues dealing with the config module."""


class BetelgeuseConfig(object):
    """Configuration object for Betelgeuse."""

    def __init__(self, config_module=None):
        """Initialize the configuration."""
        self._config_module = None
        for config in dir(default_config):
            if config.isupper():
                setattr(self, config, getattr(default_config, config))
        if config_module is not None:
            try:
                self._config_module = importlib.import_module(config_module)
            except ImportError:
                raise ConfigModuleError(
                    'Config module "{}" can\'t be imported.  Make sure it is '
                    'on the Python path.'
                    .format(config_module)
                )

            for config in dir(self._config_module):
                if config.isupper():
                    setattr(self, config, getattr(self._config_module, config))
