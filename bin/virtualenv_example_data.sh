#!/usr/bin/env bash

source <%= @root_dir %>/bin/virtualenv_activate.sh

echo "Creating user data"
python manage.py user_example_data 200 || exit

echo "Creating resource data"
python manage.py resources_example_data 50 || exit

echo "Creating applications data"
python manage.py applications_example_data 1000 || exit
