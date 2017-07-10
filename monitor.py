#!/usr/bin/python3

import os
import sys
import time
from datetime import datetime
import smtplib
import re
import getpass
import requests


# create server class
class ServerClass(object):
    address = ""
    failcount = 0
    firstfail = None
    isdown = False
    def __init__(self, address, failcount, firstfail, isdown):
        self.address = address
        self.failcount = failcount
        self.firstfail = firstfail
        self.isdown = isdown
    def set_address(self, address):
        self.address = address
    def reset_failcount(self):
        self.failcount = 0
    def increment_failcount(self):
        self.failcount += 1
    def set_firstfail(self, firstfail):
        self.firstfail = firstfail
    def reset_firstfail(self):
        self.firstfail = None
    def set_isdown(self, isdown):
        self.isdown = isdown


# create url class
class UrlClass(object):
    url = ""
    status_code = 0
    response_time = 0
    content = ""
    failcount = 0
    def __init__(self, url, status_code, response_time, content, failcount):
        self.url = url
        self.status_code = status_code
        self.response_time = response_time
        self.content = ""
        self.failcount = 0
    def set_url(self, url):
        self.url = url
    def set_status_code(self, status_code):
        self.status_code = status_code
    def set_response_time(self, response_time):
        self.response_time = response_time
    def set_content(self, content):
        self.content = content
    def increment_failcount(self):
        self.failcount += 1
    def reset_failcount(self):
        self.failcount = 0


# functions
def get_config_path():
    path = ""
    if os.path.isfile(scriptdir + "/monitor.conf"):
        path = scriptdir + "/monitor.conf"
        return path
    else:
        print("\033[91m[!]\033[0m ERROR could not find configuration file in %s" % scriptdir)
        sys.exit()

def read_config(param):
    path = get_config_path()
    fileopen = open(path, "r")
    for line in fileopen:
        if not line.startswith("#"):
            match = re.search(param + "=", line)
            if match:
                line = line.rstrip()
                line = line.replace('"', "")
                line = line.replace(' ', "")
                line = line.split(param + "=")
                return line[1]
    print("\033[91m[!]\033[0m ERROR - %s not found in %s" % (param, path))
    sys.exit()

def is_config_enabled(param):
    try:
        config = read_config(param).lower()
        return config in ("on", "yes", "y")
    except AttributeError:
        return "off"

def format_date(date):
    return date.strftime('%m-%d-%Y %H:%M:%S UTC')

def write_log(line, log_file):
    with open(log_file, 'a') as f:
        f.write("%s\n" % line)

def printlog(str):
    print(str)
    if logging: write_log("%s %s" % (format_date(datetime.now()), str.strip()), log_file)

def send_email(user, password, server, port, body):
    msg = "From: Ping Test <%s>\n\n%s" % (user, body)
    try:
        server = smtplib.SMTP(server, port)
        server.ehlo()
        server.starttls()
        server.login(user, password)
        server.sendmail(user, email_list, msg)
        server.close()
        printlog('[-] Email sent.')
    except:
        printlog('\033[91m[!]\033[0m %s Email failed to send.' % format_date(datetime.now()))


# get the directory where this script exists
scriptdir = os.path.dirname(os.path.realpath(__file__))


# configure log file
log_file = read_config("log_file")

logging = False if log_file == "" else True

if logging:
    if not os.path.isfile(log_file):
        try:
            print("[-] Creating log file %s..." % log_file)
            with open(log_file, 'a') as f:
                f.write("%s [-] Created log file\n" % format_date(datetime.now()))
        except:
            raise
            print("\033[91m[!]\033[0m ERROR - Could not create log file")
            sys.exit()


# check for internet connectivity
if os.system("ping -c 1 google.com > /dev/null 2>&1") != 0:
    printlog("\033[93m[!]\033[0m WARNING - no internet connectivity.")


# create server list
serverlist = read_config("server_list")
servers = []
if not serverlist == "":
    servervarnum = 0
    for server in serverlist.split(","):
        servervarname = "server" + str(servervarnum)
        exec(servervarname + " = ServerClass(server, 0, None, False)")
        exec("servers.append(" + servervarname + ")")
        servervarnum += 1


# create URL list
urllist = read_config("website_list")
urls = []
if not urllist == "":
    urlvarnum = 0
    for url in urllist.split(","):
        urlvarname = "url" + str(urlvarnum)
        exec(urlvarname + " = UrlClass(url, 0, 0, '', 0)")
        exec("urls.append(" + urlvarname + ")")
        urlvarnum += 1


# check if servers / URLs were provided in monitor.conf
if len(servers) == 0 and len(urls) == 0:
    printlog("\033[93m[!]\033[0m Nothing to monitor - Please provide a list of servers and/or websites to monitor in 'monitor.conf'.")
    sys.exit()


# get ping options
try:
    max_ping_fails = int(read_config("max_ping_fails"))
except:
    printlog("\033[91m[!]\033[0m ERROR - invalid 'max_ping_fails' value in monitor.conf")
    sys.exit()
try:
    ping_sleep = float(read_config("ping_sleep"))
except:
    printlog("\033[91m[!]\033[0m ERROR - invalid 'ping_sleep' value in monitor.conf")
    sys.exit()


# get website options
monitor_status_code = is_config_enabled("monitor_status_code")
monitor_content = is_config_enabled("monitor_webpage_content")
try:
    max_webpage_fails = int(read_config("max_webpage_fails"))
except:
    printlog("\033[91m[!]\033[0m ERROR - invalid 'max_webpage_fails' value in monitor.conf")
    sys.exit()


# Set email-related variables
send_email_notifications = is_config_enabled("send_email_notifications")
if send_email_notifications:
    email_list = read_config("email_list")
    email_list = email_list.split(",")
    email_user = read_config("email_user")
    email_password = read_config("email_password")
    if email_password == "": email_password = getpass.getpass('\nEnter email password for user [%s]: ' % email_user)
    email_server = read_config("email_server")
    email_port = read_config("email_port")


# Options OKAY - starting script
if logging: write_log("%s [-] Starting script" % format_date(datetime.now()), log_file)


# initial check to see if all servers are accessible
if len(servers) > 0:
    printlog("[-] Checking initial ping connectivity...\n")
    for server in servers:
        response = os.system("ping -c 1 " + server.address + " > /dev/null 2>&1")
        if response == 0:
            printlog('\033[92m[+]\033[0m UP - %s' % server.address)
        elif response == 512:
            printlog('\033[91m[!]\033[0m DNS FAIL - %s' % server.address)
        elif response == 256:
            printlog('\033[91m[!]\033[0m TIMEOUT - %s' % server.address)
        else:
            printlog('\033[91m[!]\033[0m MISC FAIL - %s' % server.address)


# make sure all URLs are formatted correctly
for url in urls:
    if not ('http://' in url.url or 'https://' in url.url):
        url.set_url("http://%s" % url.url)

# initial check to see if all websites are accessible
if len(urls) > 0:
    printlog("\n[-] Checking initial website connectivity...\n")
    for url in urls:
        try:
            r = requests.get(url.url)
            url.set_status_code(r.status_code)
            url.set_content(r.content)
            url.set_response_time(r.elapsed.total_seconds())
            printlog('\033[92m[+]\033[0m [HTTP %s] %s' % (url.status_code, url.url))
            if logging:
                write_log("%s [-] '%s' Status code: %s" % (format_date(datetime.now()), url.url, url.status_code), log_file)
                write_log("%s [-] '%s' Content length: %s" % (format_date(datetime.now()), url.url, len(url.content)), log_file)
                write_log("%s [-] '%s' Response time: %s" % (format_date(datetime.now()), url.url, url.response_time), log_file)
        except KeyboardInterrupt:
            printlog("\n[-] User exit.")
            sys.exit()
        except requests.exceptions.SSLError:
            printlog("\033[91m[!]\033[0m SSL error - %s" % url.url)
            printlog("\n[-] Quitting...")
            sys.exit()
        except requests.exceptions.ConnectionError:
            printlog("\033[91m[!]\033[0m Connection error - %s" % url.url)
            printlog("\n[-] Quitting...")
            sys.exit()
        except:
            printlog('\033[91m[!]\033[0m Unknown URL error - %s:\n\n' % url.url)
            raise
            sys.exit()


# loop through servers list, sending pings to each, waiting 1 second in between
printlog('\n[-] Monitoring hosts...\n')

# if configured, send email to say the script is starting
if is_config_enabled("send_email_on_startup"):
    onstart_msg = "\nThe system monitor script was just started.\n\nYou are receiving this notification because your email is included in the list to be notified when a system goes down.  This notification could have been triggered by a reboot of the system or by manually starting the system monitoring script."
    send_email(email_user, email_password, email_server, email_port, onstart_msg)

try:
    while True:
        # Cycle through pinging hosts
        for server in servers:
            response = os.system("ping -c 1 " + server.address + " > /dev/null 2>&1")

            # Ping SUCCESS
            if response == 0:
                if server.failcount >= max_ping_fails:
                    # Failed pings WERE over threshold, now it's pinging again.
                    printlog('\033[92m[+]\033[0m %s is back up!' % server.address)
                    if send_email_notifications:
                        # Send email saying its back up
                        message = "Server Up!\n\n%s is back up! Server was down from %s to %s." % (server.address, format_date(server.firstfail), format_date(datetime.now()))
                        send_email(email_user, email_password, email_server, email_port, message)
                server.reset_failcount()
                server.reset_firstfail()

            # Ping FAIL
            else:
                if server.failcount == 0:
                    # if this is the first fail, take a timestamp
                    server.set_firstfail(datetime.now())
                server.increment_failcount()
                if response == 512:
                    failreason = 'DNS failure'
                elif response == 256:
                    failreason = 'Ping timeout'
                else:
                    failreason = 'Unknown ping failure code: ' + response
                printlog('\033[93m[!]\033[0m %s - %s' % (server.address, failreason))
                if server.failcount == max_ping_fails:
                    # Failed pings are over threshold
                    printlog('\033[91m[!]\033[0m %s is down!' % server.address)
                    if send_email_notifications:
                        # Send an email saying the server is down
                        message = "Server Down!\n\n%s is down.\n\nNo pings since %s\n\nDetails: %s" % (server.address, format_date(server.firstfail), failreason)
                        send_email(email_user, email_password, email_server, email_port, message)
            time.sleep(ping_sleep)

        # Cycle through websites
        for url in urls:
            try:
                r = requests.get(url.url)
                message = ""
                if url.failcount >= max_webpage_fails:
                    printlog("\033[92m[+]\033[0m %s is back up!" % url.url)
                    message += "\n%s is back up!\n"
                    url.reset_failcount()
                if r.status_code != url.status_code:
                    if monitor_status_code:
                        printlog("\033[93m[!]\033[0m %s status code has changed from %s to %s." % (url.url, url.status_code, r.status_code))
                        message += "\n%s status code has changed from %s to %s.\n" % (url.url, url.status_code, r.status_code)
                    url.set_status_code(r.status_code)
                if len(r.content) != len(url.content):
                    if monitor_content:
                        printlog("\033[93m[!]\033[0m %s response content has changed." % (url.url))
                        message += "\n%s response content has changed.\n" % (url.url)
                    url.set_content(r.content)
                url.set_response_time(r.elapsed.total_seconds())
                if message != "" and send_email_notifications:
                    send_email(email_user, email_password, email_server, email_port, message)
            except KeyboardInterrupt:
                printlog("\n[-] User exit.")
                sys.exit()
            except requests.exceptions.SSLError:
                printlog('\033[91m[!]\033[0m %s - HTTP request failed! SSL error.' % url.url)
                url.increment_failcount()
                if url.failcount == max_webpage_fails:
                    if send_email_notifications:
                        message = "\nWebsite Down!\n\n%s request(s) to %s failed.\n\nDetails: SSL error" % (max_webpage_fails, url.url)
                        send_email(email_user, email_password, email_server, email_port, message)
            except requests.exceptions.ConnectionError:
                printlog('\033[91m[!]\033[0m %s - HTTP request failed! Connection error' % url.url)
                url.increment_failcount
                if url.failcount == max_webpage_fails:
                    if send_email_notifications:
                        message = "\nWebsite Down!\n\n%s request(s) to %s failed.\n\nDetails: Connection error" % (max_webpage_fails, url.url)
                        send_email(email_user, email_password, email_server, email_port, message)
            except:
                printlog('\033[91m[!]\033[0m %s - Unknown error!' % url.url)
                raise

            time.sleep(ping_sleep)


except KeyboardInterrupt:
    printlog("\n[-] User exit.")
    sys.exit()
