# -*- coding: utf-8 -*-
from .auth import auth_bp
from .targets import targets_bp
from .attacks import attacks_bp
from .defenses import defenses_bp, defenses_alt_bp
from .logs import logs_bp
from .stats import stats_bp
from .topology import topology_bp
from .compat import compat_bp
from .agents import agents_bp

# 注册所有蓝图
all_blueprints = [
    compat_bp,
    auth_bp,
    targets_bp,
    attacks_bp,
    defenses_bp,
    defenses_alt_bp,
    logs_bp,
    stats_bp,
    topology_bp,
    agents_bp
]

__all__ = ['all_blueprints']