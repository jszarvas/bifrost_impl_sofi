#!/bin/bash 
#PBS -A ssi_disease_surveillance
#PBS -l nodes=1:ppn=4,mem=12gb,walltime=03:00:00
#PBS -W group_list=ssi_disease_surveillance
#PBS -W x=advres:ssi_disease_surveillance_wiki_ssi.313

cd /home/projects/fvst_ssi_dtu/test_app/scripts/singularity
source ../../settings/singularity_settings.sh
source ../../settings/env_vars.sh

module load tools
#module load $SINGULARITY_VERSION

re="^(.*?)__(.*)$"
for image in ${BIFROST_COMPONENT_LIST[@]}; do
name=${image%%__*}
version=${image#*__}
echo "Downloading ${name}__${version}"
echo "singularity build -F --sandbox ${name}__${version} docker://ssidk/${name}:${version}"
#singularity build -F --sandbox ${name}__${version} docker://ssidk/${name}:${version}
done
