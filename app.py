# -*- coding: utf-8 -*-
"""
Created on Mon Mar 16 22:55:18 2015

@author: Noah McDougall
"""
import imp
import os
import cherrypy

#
#  main():
#

if __name__ == '__main__':
   ip   = os.environ['OPENSHIFT_PYTHON_IP']
   port = int(os.environ['OPENSHIFT_PYTHON_PORT'])
   app = imp.load_source('application.py', 'wsgi/application.py')
   
   
   ## Sets up logging ##
   appserver_error_log = os.path.join(os.environ['OPENSHIFT_PYTHON_LOG_DIR'], 'appserver_error.log')
   appserver_access_log = os.path.join(os.environ['OPENSHIFT_PYTHON_LOG_DIR'], 'appserver_access.log')
 
   cherrypy.config.update({
                   'log.screen': True,
                   'server.socket_host': ip,
                   'server.socket_port': port,
                   'log.error_file': appserver_error_log,
                   'log.access_file': appserver_access_log
   })
    
   fwtype="wsgiref"
   for fw in ("cherrypy"):
      try:
         imp.find_module(fw)
         fwtype = fw
      except ImportError:
         pass




   print('Starting WSGIServer type %s on %s:%d ... ' % (fwtype, ip, port))
   if fwtype == "cherrypy":
      from cherrypy import wsgiserver
      server = wsgiserver.CherryPyWSGIServer(
         (ip, port), app.application, server_name=os.environ['OPENSHIFT_APP_DNS'])
      server.start()

   else:
      from wsgiref.simple_server import make_server
      make_server(ip, port, app.application).serve_forever()