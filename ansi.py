# -*- coding: utf-8 -*-

"""Listing of ANSI colors plus additional Windows support."""

import platform

# Needed to make ANSI escape sequences work in Windows
SYSTEM = platform.system()
if SYSTEM == "Windows":
    try:
        import colorama
        colorama.init()
    except ImportError:
        pass

UP_DEL = u"\u001b[F\u001b[K"
SCP = u"\u001b[s"
RCP = u"\u001b[u"
EL = u"\u001b[K"
EL_LEFT = u"\u001b[1K"
EL_ALL = u"\u001b[2K"
BLACK = u"\u001b[0;30m"
RED_DARK = u"\u001b[0;31m"
GREEN_DARK = u"\u001b[0;32m"
YELLOW_DARK = u"\u001b[0;33m"
CYAN_DARK = u"\u001b[0;36m"
SILVER = u"\u001b[0;37m"
GREY = u"\u001b[1;30m"
RED = u"\u001b[1;31m"
GREEN = u"\u001b[1;32m"
YELLOW = u"\u001b[1;33m"
CYAN = u"\u001b[1;36m"
WHITE = u"\u001b[1;37m"
RESET = u"\u001b[0m"
