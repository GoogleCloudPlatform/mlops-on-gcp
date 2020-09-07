#!/bin/bash
if [[ -x "/init.sh" ]]; then
    /init.sh
fi
if [[ -z "${DL_ANACONDA_HOME}" ]]; then
    # Notebook environment
    . "${DL_ANACONDA_HOME}/etc/profile.d/conda.sh"
    conda activate base
    exec "$@"
else
    # Training environment
    exec python3 /mltrainer/mlrunner.py $@
fi