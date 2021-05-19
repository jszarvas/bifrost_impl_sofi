#!/bin/bash 
#PBS -A ssi_disease_surveillance
#PBS -l nodes=1:ppn=4,mem=12gb,walltime=03:00:00
#PBS -W group_list=ssi_disease_surveillance
#PBS -W x=advres:ssi_disease_surveillance_wiki_ssi.313

cd /home/projects/fvst_ssi_dtu/test_app/scripts/singularity
module load tools
module load singularity/3.6.4
source ../../settings/singularity_settings.sh

echo "Downloading $1__$2"
echo "singularity build -F --sandbox $1__$2 docker://ssidk/$1:$2"
singularity build -F --sandbox $1__$2 docker://ssidk/$1:$2
