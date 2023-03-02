# formcollector
a simple webserver that can be configured through a rest api. You send it an html template with a place holder. The server replaces the place holder with a unique submission link per identity. You can email the link to people where they can perform a submission. I'd like to think of this as a minimal survey-monkey kind of  applicaiton. The primary use-case for this was to serve as a remote data collection task sever for Cortex XSOAR; but it can be used by a client application to serve html pages and poll for responses.

The client code is present in sample-server.py. 

The server stores everything in mongodb collections.

To run do docker-compose up.

Observe the .env file to configure the server with a secret key and some other parameters. 
start.sh creates a self-signed http cert by default, unless you put your own certificate there.
