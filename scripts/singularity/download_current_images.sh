#!/bin/bash 
#PBS -A fvst_ssi_dtu
#PBS -l nodes=1:ppn=4,mem=12gb,walltime=03:00:00
#PBS -W group_list=fvst_ssi_dtu
#PBS -W x=advres:fvst_ssi_dtu_wiki_fodevarestyrelsen.16

cd /home/projects/fvst_ssi_dtu/test_app/scripts/singularity
source ../../settings/env_vars.sh

module load tools
module load $SINGULARITY_VERSION
source ../../settings/singularity_settings.sh

#re="^(.*?)__(.*)$"
for image in ${BIFROST_COMPONENT_LIST[@]}; do
    name=${image%%__*}
    version=${image#*__}
    echo "Downloading ${name}__${version}"
    echo "singularity build -F --sandbox ${name}__${version} docker://ssidk/${name}:${version}"
    singularity build -F --sandbox ${name}__${version} docker://ssidk/${name}:${version}
    singularity run ${name}__${version} --info
done
