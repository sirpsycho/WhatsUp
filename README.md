# WhatsUp
Monitors websites, servers, and desktops

# Description
Monitor a list of hosts via ping and/or web requests.  This utility provides a configuration file that can be edited to provide a range of functionality.  Add servers and web URLs to get notified when they go down or when changes are made.

# Features
- Send email alerts when a host comes up or down
- Alert on changes in HTTP response codes ("200 OK", "404 NOT FOUND", "503 SERVER ERROR", etc.)
- Optional logging feature

# Setup
Edit `monitor.conf` using a text editor of your choice.  Add the hosts you would like to monitor and configure the various options.  Then run `./monitor.py` to begin monitoring.
