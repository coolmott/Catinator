#!/bin/bash
ARCHIVE_PATH=/var/lib/motion
find $ARCHIVE_PATH -name '*.avi' -mtime +30 -exec rm {} \;
find $ARCHIVE_PATH -name '*.jpg' -mtime +30 -exec rm {} \;
find $ARCHIVE_PATH -name '*.mpg' -mtime +30 -exec rm {} \;
