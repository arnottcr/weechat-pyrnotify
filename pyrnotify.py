# -*- coding: utf-8 -*-
# ex:sw=4 ts=4:ai:
#
# Copyright (c) 2012 by Krister Svanlund <krister.svanlund@gmail.com>
#   based on tcl version:
#    Remote Notification Script v1.1
#    by Gotisch <gotisch@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

# Example usage when Weechat is running on a remote PC and you want
# want to use port 4321 for the connection.
#
#     On the "client" (where the notifications will end up), host is
#     the remote host where weechat is running:
#        python2 location/of/pyrnotify.py 4321 & ssh -R 4321:localhost:4321 username@host
#     You can have a second argument to specified the time to display the notification
#       python2 location/of/pyrnotify.py 4321 2000 & ssh -R 4321:localhost:4321 username@host
#     Important to remember is that you should probably setup the
#     connection with public key encryption and use something like
#     autossh to do this in the background.
#
#     In weechat:
#        /python load pyrnotify.py
#        and set the port
#        /set plugins.var.python.pyrnotify.port 4321
#
# It is also possible to set which host pyrnotify shall connect to,
# this is not recommended. Using a ssh port-forward is much safer
# and doesn't require any ports but ssh to be open.

# ChangeLog:
#
# 2014-05-10: Change hook_print callback argument type of displayed/highlight
#             (WeeChat >= 1.0)
# 2012-06-19: Added simple escaping to the title and body strings for
#             the script to handle trailing backslashes.

try:
    import weechat as w
    in_weechat = True
except ImportError as e:
    in_weechat = False

import os, sys, re
import socket
import subprocess
import shlex

SCRIPT_NAME         = "pyrnotify"
SCRIPT_COLLABORATOR = "Krister Svanlund <krister.svanlund@gmail.com>"
SCRIPT_AUTHOR       = "Colin Arnott <colin@urandom.co.uk>"
SCRIPT_VERSION      = "1.0"
SCRIPT_LICENSE      = "GPL3"
SCRIPT_DESC         = "Send remote notifications over SSH"
SCRIPT_USAGEINFO    = '''
Usage:
	pyrnotify.py [( -s | --socket ) <socket suffix> | <port>]

	<socket suffix>     suffix of the socket /tmp/libnotify_remote-<suffix>.sock
	<port>              tcp port used by socket

Note:
	socket or port must be forwarded to remote machine manually
'''

def run_notify(urgency, nick,chan,message):
    try:
        if w.config_is_set_plugin('socket'):
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            s.connect(w.config_get_plugin('socket'))
        else:
            host = w.config_get_plugin('host')
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((host, int(w.config_get_plugin('port'))))
        s.send("%s %s \"%s to %s\" \"%s\"" % (urgency, socket.gethostname(), nick, chan, message))
        s.close()
    except Exception as e:
        w.prnt("", "Could not send notification: %s" % str(e))

def on_msg(*a):
    if len(a) == 8:
        data, buffer, timestamp, tags, displayed, highlight, sender, message = a
        if data == "private" or int(highlight):
            if data == "private":
                urgency = "critical"
            else:
                urgency = "normal"
            buffer = "me" if data == "private" else w.buffer_get_string(buffer, "short_name")
            run_notify(urgency, sender, buffer, message)
            #w.prnt("", str(a))
    return w.WEECHAT_RC_OK

def weechat_script():
    settings = {'host' : "localhost",
                'port' : "4321",
                'icon' : "utilities-terminal",
                'pm-icon' : "emblem-favorite"}
    if w.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, "", ""):
        for (kw, v) in settings.items():
            if not w.config_get_plugin(kw):
                w.config_set_plugin(kw, v)
        w.hook_print("", "notify_message", "", 1, "on_msg", "")
        w.hook_print("", "notify_private", "", 1, "on_msg", "private")
        w.hook_print("", "notify_highlight", "", 1, "on_msg", "") # Not sure if this is needed






######################################
## This is where the client starts, except for the global if-check nothing below this line is
## supposed to be executed in weechat, instead it runs when the script is executed from
## commandline.

def escape(s):
    if '&' in s:
        s = re.sub(r'&',r'&amp;',s)
    if '<' in s:
        s = re.sub(r'<',r'&lt;',s)
    return s


def accept_connections(s):
    conn, addr = s.accept()
    try:
        data = ""
        d = conn.recv(1024)
        while d:
            data += d
            d = conn.recv(1024)
    finally:
        conn.close()
    if data:
        try:
            urgency, host, title, body = shlex.split(data)
            subprocess.call(["notify-send", "-u", urgency, "-a", "IRC %s" % host, escape(title), escape(body)])

        except ValueError as e:
            print e
        except OSError as e:
            print e
    accept_connections(s)

def weechat_client(argv):
    if len(sys.argv) < 3:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("localhost", int(argv[1] if len(sys.argv) > 1 else 4321)))
    elif len(sys.argv) == 3 and (argv[1] == '-s' or argv[1] == '--socket'):
        socket_address = argv[2]
        # Make sure the socket does not already exist
        try:
            os.unlink(socket_address)
        except OSError:
            if os.path.exists(socket_address):
                raise
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.bind(socket_address)
    else:
        print SCRIPT_USAGEINFO
        sys.exit()

    s.listen(5)
    try:
        accept_connections(s)
    except KeyboardInterrupt as e:
        print "Keyboard interrupt"
        print e
    finally:
        s.close()

if __name__ == '__main__':
    if in_weechat:
        weechat_script()
    else:
        weechat_client(sys.argv)
