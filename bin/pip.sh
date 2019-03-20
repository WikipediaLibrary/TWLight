#!/usr/bin/env bash

# add the app to pythonpath
echo "export PYTHONPATH=\"/usr/lib/python2.7\"; export PYTHONPATH=\"\${PYTHONPATH}:/app\"" > /etc/profile.d/pypath.sh
pip install setuptools --upgrade
pip install -r requirements/wmf.txt --ignore-installed
