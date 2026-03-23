#!/bin/bash
# git-log-timewindow.sh
# Ausgabe aller Commits mit lesbarem Zeitstempel, optional mit --since / --until

git log --pretty=format:'%h %an %ad %s' --date=iso "$@"
