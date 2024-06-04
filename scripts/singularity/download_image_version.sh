#!/bin/bash 
#PBS -A fvst_ssi_dtu
#PBS -l nodes=1:ppn=4,mem=12gb,walltime=03:00:00
#PBS -W group_list=fvst_ssi_dtu
#PBS -W x=advres:fvst_ssi_dtu_wiki_fodevarestyrelsen.16
#PBS -v BASE_DIR

if [ "x$BASE_DIR" == "x" ]; then
    echo "\$BASE_DIR not set. Exiting"
    exit
fi

cd $BASE_DIR/scripts/singularity
source $BASE_DIR/settings/env_vars.sh

module load tools
module load $SINGULARITY_VERSION
source $BASE_DIR/settings/singularity_settings.sh

echo "Downloading $1__$2"
echo "singularity build --sandbox -F $1__$2 docker://ssidk/$1:$2"
singularity build --sandbox -F $1__$2 docker://ssidk/$1:$2

echo "singularity run $1__$2 --info"
singularity run $1__$2 --info
