#!/bin/bash

# shellcheck disable=SC2078
while [ True ]; do
  if [ "$1" = "--dir" -o "$1" = "-d" ]; then
      echo "Changing Working directory in $2"
      COVERAGE_PATH=".$2/coverage.cobertura.xml"
      shift 1
  else
      break
  fi
done

VENV_NAME="venv"

[ -d $VENV_NAME ] && rm -rf $VENV_NAME

python3.12 -m venv $VENV_NAME
source $VENV_NAME/bin/activate

# Set the environment variable
export ENV="test"

set -o errexit

pip3.12 install --trusted-host nexus.inps.it --index-url=http://nexus.inps.it/repository/python-group/simple --upgrade pip==23.3.2
pip3.12 install -vvv --trusted-host nexus.inps.it --index-url=http://nexus.inps.it/repository/python-group/simple -r requirements-test.txt


if [ $? -eq 0 ]; then
  echo "All dependencies installed!"
else
  echo "Error during dependencies setup!"
  exit 1
fi

pytest --cov --cov-report=xml:.${SYSTEM_DEFAULTWORKINGDIRECTORY}/cobertura.coverage.xml --cov-branch --junitxml=cobertura.coverage.xml

if [[ -f ".${SYSTEM_DEFAULTWORKINGDIRECTORY}/coverage.cobertura.xml" ]]; then
    echo "coverage file successfully generated!"
fi

echo "Deactivating virtual environment"
deactivate
[ -d $VENV_NAME ] && rm -rf $VENV_NAME