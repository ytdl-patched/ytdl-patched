#!/bin/bash

wget https://repo1.maven.org/maven2/org/python/jython-installer/2.7.2/jython-installer-2.7.2.jar
wget https://files.pythonhosted.org/packages/99/4f/13fb671119e65c4dce97c60e67d3fd9e6f7f809f2b307e2611f4701205cb/nose-1.3.7-py2-none-any.whl

java -jar jython-installer-2.7.2.jar -s -d "$HOME/jython"
"$HOME"/jython/bin/jython -m pip install nose-1.3.7-py2-none-any.whl

if [ "x$GITHUB_ACTION" != "x" ]; then
    echo "$HOME/jython/bin" >> "$GITHUB_PATH"
fi
