# -*- coding: utf-8 -*-
"""
Created on Tue Mar  3 21:22:21 2015

@author: Noah McDougall
"""
import csv
import numpy as np
import math
import cherrypy
import jinja2
import os.path

env = jinja2.Environment(loader=jinja2.FileSystemLoader('templates'))

class Application:
    @cherrypy.expose
    def index(self):
        if os.path.exists('./data/faults.csv'):
            cherrypy.session['filecache'] = 1
            tmpl = env.get_template('index_yescache.html')
        else:
            cherrypy.session['filecache'] = 0
            tmpl = env.get_template('index_nocache.html')
    
        return tmpl.render()  
     
    ## Uploader ##
    @cherrypy.expose 
    def upload(self,myFile):       
        
        all_data = bytearray()
        
        while True:
            data = myFile.file.read(8192)
        
            all_data += data
        
            if not data:
                break
        
        saved_file=open('./data/faults.csv', 'wb') 
        saved_file.write(all_data) 
        saved_file.close()
        
        raise cherrypy.HTTPRedirect("/")
    
    ## Processor ##    
    @cherrypy.expose
    def processdata(self):
        ## Importing and organizing data into (x,y,z) tuple based on fault name ##
        with open('./data/faults.csv', 'rt') as datalist:
                reader = csv.reader(datalist, delimiter=",")
                faults = dict()
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
            plane.append((np.matrix(xyone[i],dtype=np.int64).T*np.matrix(xyone[i],dtype=np.int64))**-1*np.matrix(xyone[i],dtype=np.int64).T*np.matrix(z[i],dtype=np.int64).T)    
       
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
            if dipdirection[i] == "Northwest" and unadjustedstrike[i] > 180:
                faultstrike.append(unadjustedstrike[i] - 180)
            elif dipdirection[i] == "Southwest" and unadjustedstrike[i] > 180:
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
            dipangle.append(np.degrees(math.acos((u[i][0]*v[i][0]+u[i][1]*v[i][1]+u[i][2]*v[i][2])/(Us[i]*Vs[i]))))

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
        
#    @cherrypy.expose
#    def plotdata(self):
#        faults = cherrypy.session['faults']     
#
#        x = []
#        y = []
#        z = []        
#                
#        for i in range(0, len(faults['njm_SB_022'])):
#            x.append(faults['njm_SB_022'][i][0])
#            y.append(faults['njm_SB_022'][i][1])
#            z.append(faults['njm_SB_022'][i][2])
#            
#        tmpl = env.get_template('plotdata.html')
#        
#        return tmpl.render()  

## Turns on sessions so you can carry variables across methods ##
if __name__ == '__main__':
     conf = {
         '/': {
             'tools.sessions.on': True
         }
     }
     cherrypy.quickstart(Application(), '/', conf)


cherrypy.quickstart(Application())