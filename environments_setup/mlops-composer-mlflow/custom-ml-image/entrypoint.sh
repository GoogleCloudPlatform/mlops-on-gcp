#!/bin/bash
for i in "$@" ; do
    if [[ $i == --job-dir* ]]; then
        TRAINING_JOB=True 
        echo 'Training job'
        break
    fi 
done

if [[ -x "/init.sh" ]]; then
    /init.sh
fi

if [[ -z "${TRAINING_JOB}" ]]; then
    # Notebook environment
    . "${DL_ANACONDA_HOME}/etc/profile.d/conda.sh"
    conda activate base
    exec "$@"
    /run_jupyter.sh
else
    # Training environment
    exec python3 /mltrainer/mlrunner.py $@
fi
