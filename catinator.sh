#! /bin/sh
# /etc/init.d/catinator.sh

# Supplied for the catinatord.py 
# Modified for Debian GNU/Linux by James M. Coulthard <james.m.coulthard@gmail.com>

# LSB Init Script Block
### BEGIN INIT INFO
# Provides:				catinator
# Required-Start:		$all
# Required-Stop:		$all
# Default-Start:		3 4 5
# Default-Stop:			0 1 2 6
# Short-Description:	Start The Catinator at boot
# Description:			The Catinator start up script; starts catinatord.py
### END INIT INFO


# . /etc/rc.d/init.d/functions  # uncomment/modify for your killproc

DAEMON=/home/pi/projects/Catenatitor/catinatord.py
INIT=/home/pi/projects/Catenatitor/catinator_init.py
OPTS='-c /home/pi/projects/Catenatitor/Catinator.conf.xml'
PIDFILE=/var/run/catinatord.py.pid
NAME=catinator

test -x $DAEMON || exit 0
test -x $INIT || exit 0

case "$1" in
    start)
    echo -n "Starting The Catinator: "
    start-stop-daemon --start --pidfile $PIDFILE --startas $INIT --exec $DAEMON -- $OPTS
    ;;
    stop)
    echo -n "Shutting down The Catinator: "
    start-stop-daemon --stop --oknodo --retry 30 --pidfile $PIDFILE
    echo "Hasta la vista, baby!!"
    ;;
    restart)
    echo -n "Restarting The Catinator: "
    start-stop-daemon --stop --oknodo --retry 30 --pidfile $PIDFILE
    start-stop-daemon --start --pidfile $PIDFILE --startas $INIT --exec $DAEMON -- $OPTS
    ;;

    *)
    echo "Usage: $0 {start|stop|restart}"
    exit 1
esac
exit 0

