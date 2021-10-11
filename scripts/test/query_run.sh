#!/bin/bash 
#PBS -A fvst_ssi_dtu
#PBS -l nodes=1:ppn=4,mem=1gb,walltime=01:00:00
#PBS -W group_list=fvst_ssi_dtu
#PBS -W x=advres:fvst_ssi_dtu_wiki_fodevarestyrelsen.16

runpath=$1
runname=`basename $runpath`

echo $runname

source /home/projects/fvst_ssi_dtu/test_app/settings/env_vars.sh

module load tools
module load mongodb/4.4.1


mongo $BIFROST_DB_KEY <<EOF
db
db.samples.find({"name":/$runname/})
db.runs.find({"name":/$runname/})
db.sample_components.find({"name":/$runname/})
EOF

echo rm -r $runpath
