#!/bin/bash
kill -s KILL $(ps wuax | awk 'NR>1 && $8 ~ "T" {print $2}') &
killall aria2c &
make clean &
