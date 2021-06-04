#!/bin/bash 
#PBS -A fvst_ssi_dtu
#PBS -l nodes=1:ppn=4,mem=12gb,walltime=03:00:00
#PBS -W group_list=fvst_ssi_dtu
#PBS -W x=advres:fvst_ssi_dtu_wiki_fodevarestyrelsen.16

cd $BASE_DIR/singularity
module load tools
module load singularity/3.6.4
source $BASE_DIR/settings/singularity_settings.sh

echo "Downloading $1__$2"
echo "singularity build -F --sandbox $1__$2 docker://ssidk/$1:$2"
singularity build -F --sandbox $1__$2 docker://ssidk/$1:$2
