# -*- coding: utf-8 -*-
import os

HOST = os.getenv("MYTOOLS_HOST", "127.0.0.1")
PORT = int(os.getenv("MYTOOLS_PORT", "8765"))
