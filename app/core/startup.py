"""Reserved startup adapter; do not silently modify the Windows registry."""


class StartupService:
    supported = False

    def set_enabled(self, enabled):
        # TODO: add an explicit, reversible HKCU Run adapter after packaging.
        if enabled:
            raise NotImplementedError("v0.1 暂未实现开机启动")
