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
env = jinja2.Environment(loader=jinja2.FileSystemLoader('/home/noahmcdougall/GeoStriker/wsgi/static'))

if cherrypy.__version__.startswith('3.') and cherrypy.engine.state == 0:
    cherrypy.engine.start(blocking=False)
    atexit.register(cherrypy.engine.stop)


class calculate:
    @cherrypy.expose
    def index(self):
        tmpl = env.get_template('index.html')
        return tmpl.render()

    ## Processor ##
    @cherrypy.expose
    def processdata(self, myFile):
        faults = {}
        reader = csv.reader(myFile.file)
        for row in reader:
            if row[3] not in faults:
                faults[row[3]] = []
            faults[row[3]].append((int(row[0]),int(row[1]),int(row[2])))


        ## Saves faults XYZ data into a session variable ##
        cherrypy.session['faults'] = faults

        ## Creates a list of Z values ##
        z=[[n[2] for n in faults[i]] for i in faults.keys()]

        ## Pulls (X,Y,1) points for every fault... list->list->int ##
        xyone = [[(n[0], n[1], 1) for n in faults[i]] for i in faults.keys()]

        ## Returns the coefficients of the best fit plane ##
        ## (At * A)^-1 * At * z
        plane = []
        for i in range(0, len(xyone)):
            plane.append((np.matrix(xyone[i],dtype=np.int64).T*np.matrix(xyone[i],dtype=np.int64))**-1 * (np.matrix(xyone[i],dtype=np.int64).T*np.matrix(z[i],dtype=np.int64).T))

        ## Gives a list of fault strikes, unadjusted for right hand rule ##
        tempunadjustedstrike = []
        unadjustedstrike = []
        for i in range(0, len(plane)):
            tempunadjustedstrike.append(90 - np.degrees(np.arctan(plane[i][0]/-plane[i][1])))
            unadjustedstrike.append(tempunadjustedstrike[i].tolist())
        unadjustedstrike = sum(unadjustedstrike, [])
        unadjustedstrike = sum(unadjustedstrike, [])

        ## Gives the dip direction ##
        dipdirection = []
        for i in range(0, len(plane)):
            if plane[i][0] < 0 and plane[i][1] < 0:
                dipdirection.append("Northeast")
            elif plane[i][0] > 0 and plane[i][1] < 0:
                dipdirection.append("Northwest")
            elif plane[i][0] > 0 and plane[i][1] > 0:
                dipdirection.append("Southwest")
            elif plane[i][0] < 0 and plane[i][1] > 0:
                dipdirection.append("Southeast")
            elif plane[i][0] == 0 and plane[i][1] > 0:
                dipdirection.append("Due South")
            elif plane[i][0] == 0 and plane[i][1] < 0:
                dipdirection.append("Due North")
            elif plane[i][0] > 0 and plane[i][1] == 0:
                dipdirection.append("Due West")
            elif plane[i][0] < 0 and plane[i][1] == 0:
                dipdirection.append("Due East")

        # Gives a list of fault strikes, adjusted for right hand rule ##
        faultstrike = []
        for i in range(0, len(plane)):
            if dipdirection[i] == "Northwest" and unadjustedstrike[i] < 180:
                faultstrike.append(unadjustedstrike[i] + 180)
            elif dipdirection[i] == "Southwest" and unadjustedstrike[i] > 180:
                faultstrike.append(unadjustedstrike[i] - 180)
            elif dipdirection[i] == "Northeast" and unadjustedstrike[i] < 180:
                faultstrike.append(unadjustedstrike[i] + 180)
            elif dipdirection[i] == "Southeast" and unadjustedstrike[i] > 180:
                faultstrike.append(unadjustedstrike[i] - 180)
            elif dipdirection[i] == "Due South" and unadjustedstrike[i] == 270:
                faultstrike.append(unadjustedstrike[i] - 180)
            elif dipdirection[i] == "Due North" and unadjustedstrike[i] == 90:
                faultstrike.append(unadjustedstrike[i] + 180)
            elif dipdirection[i] == "Due West" and unadjustedstrike[i] == 0:
                faultstrike.append(unadjustedstrike[i] + 180)
            elif dipdirection[i] == "Due East" and unadjustedstrike[i] == 180:
                faultstrike.append(unadjustedstrike[i] - 180)
            else:
                faultstrike.append(unadjustedstrike[i])


        # Sets up the process of getting dip angle ##
        dipstepone = []
        for i in range(0, len(plane)):
            dipstepone.append(plane[i].tolist())

        dipsteptwo = []
        for i in range(0, len(plane)):
            dipsteptwo.append(sum([dipstepone[i][0],dipstepone[i][1],[0]],[]))

        u = []
        v = []
        for i in range(0, len(dipsteptwo)):
            u.append([dipsteptwo[i][0]*-1, dipsteptwo[i][1]*-1,0])
            v.append([dipsteptwo[i][0]*-1, dipsteptwo[i][1]*-1,(dipsteptwo[i][0]**2)*-1 - (dipsteptwo[i][1]**2)])

        Us = []
        for i in range(0, len(plane)):
            Us.append((u[i][0]**2+u[i][1]**2)**(1/2))

        Vs = []
        for i in range(0, len(plane)):
            Vs.append((v[i][0]**2+v[i][1]**2+v[i][2]**2)**(1/2))

        ## Calculates dip angle using acos(u dot v / ||u||*||v||) ##
        dipangle = []
        for i in range(0, len(plane)):
            dipangle.append(np.degrees(math.acos((u[i][0] * v[i][0] + u[i][1] * v[i][1] + u[i][2] * v[i][2])/(Us[i] * Vs[i]))))

        ## Returns fault name, rounded strike, rounded dip angle, and dip direction ##
        faultskeys = list(faults.keys())
        answers = []
        for i in range(0, len(plane)):
            answers.append({'name' : faultskeys[i], 'strike' : str(round(faultstrike[i],1)), 'dip' : str(round(dipangle[i],1)), 'direction' : str(dipdirection[i]), 'a' : float(plane[i][0]), 'b' : float(plane[i][1]),
                            'c' : float(plane[i][2])})
        cherrypy.session['processeddata'] = answers

        raise cherrypy.HTTPRedirect("/displayprocesseddata")

    ## Displays table of data ##
    @cherrypy.expose
    def displayprocesseddata(self):
        tmpl = env.get_template('exportdata.html')
        return tmpl.render(answers = cherrypy.session['processeddata'])


application = cherrypy.Application(calculate(), '/', conf)
