#!/usr/bin/env python
import sys
sys.stdout = sys.stderr

import atexit
import cherrypy
import csv
import numpy as np
import math
import jinja2
import os.path
import io

## Sessions enabled ##
wsgi_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)))
conf = {
         '/': {
             'tools.sessions.on': True
         },
         '/static': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': os.path.join(wsgi_dir, 'assets'),
        }
    }


## Setting up jinja2's web template stuff ##
env = jinja2.Environment(loader=jinja2.FileSystemLoader('/'))

if cherrypy.__version__.startswith('3.') and cherrypy.engine.state == 0:
    cherrypy.engine.start(blocking=False)
    atexit.register(cherrypy.engine.stop)


#
