#!/bin/bash 
#PBS -A fvst_ssi_dtu
#PBS -l nodes=1:ppn=4,mem=12gb,walltime=03:00:00
#PBS -W group_list=fvst_ssi_dtu
#PBS -W x=advres:fvst_ssi_dtu_wiki_fodevarestyrelsen.16

cd /home/projects/fvst_ssi_dtu/test_app/scripts/singularity
module load tools
module load singularity/3.6.4
source ../../settings/singularity_settings.sh

echo "singularity run --info $1__$2"
singularity run $1__$2 --info
