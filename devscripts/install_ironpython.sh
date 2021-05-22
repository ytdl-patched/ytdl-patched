#!/bin/bash
set -xe

mkdir -p "$HOME/.ironpython" || true
cd "$HOME/.ironpython"

wget https://github.com/IronLanguages/ironpython2/releases/download/ipy-2.7.11/IronPython.2.7.11.zip -O ipy.zip
yes y | unzip ipy.zip || true
mkdir bin/ || true
echo -e "#!/bin/bash\nmono $PWD/net45/ipy.exe \"\$@\"" > ./bin/ironpy
chmod a+x ./bin/ironpy
export PATH="$PWD/bin:$PWD/net45:$PATH"
export IRONPYTHONPATH="$PWD/lib/python2.7/site-packages/"
ironpy -X:Frames -m ensurepip
ironpy -X:Frames -m pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org nose

sed -i "s%$PWD/net45/ipy.exe%$PWD/bin/ironpy%" ./bin/nosetests
chmod a+x ./bin/nosetests
which nosetests

if [ "x$GITHUB_ACTION" != "x" ]; then
    echo -e "$PWD/bin" >> $GITHUB_PATH
    echo -e "$PWD/net45" >> $GITHUB_PATH
    echo IRONPYTHONPATH="$PWD/lib/python2.7/site-packages/" >> $GITHUB_ENV
    echo PYTHON_HAS_MULTIPROCESSING=no >> $GITHUB_ENV
fi

true "Done! IronPython installed at $PWD"
