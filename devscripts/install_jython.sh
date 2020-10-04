#!/bin/bash

wget https://repo1.maven.org/maven2/org/python/jython-installer/2.7.2/jython-installer-2.7.2.jar
java -jar jython-installer-2.7.2.jar -s -d "$HOME/jython"
$HOME/jython/bin/jython -m pip install nose
