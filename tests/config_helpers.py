"""Test helpers — config module reload that preserves the singleton."""


def reload_config():
    """Reload the config module while preserving the singleton instance.

    importlib.reload() alone replaces the module-level config instance, but
    other modules (gateway_core, routers, main) keep references to the OLD
    instance — later tests then mutate a different object than the gateway
    actually uses (flaky failures depending on test collection order).

    This helper reloads the module for fresh class attributes (they are
    evaluated at module load time from os.environ), then copies the new
    values back into the old instance and re-points the module attribute at
    it, so every module keeps using one consistent config object.
    """
    import importlib
    import config as cfg_mod

    old_instance = cfg_mod.config
    importlib.reload(cfg_mod)
    new_instance = cfg_mod.config
    old_instance.__dict__.update(new_instance.__dict__)
    cfg_mod.config = old_instance
    return old_instance
