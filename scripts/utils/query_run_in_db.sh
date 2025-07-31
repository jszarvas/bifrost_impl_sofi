#!/bin/bash 
#PBS -A fvst_ssi_dtu
#PBS -l nodes=1:ppn=4,mem=1gb,walltime=01:00:00
#PBS -W group_list=fvst_ssi_dtu
#PBS -W x=advres:fvst_ssi_dtu_wiki_fodevarestyrelsen.16

runpath=$1
runname=`basename $runpath`

echo $runname

module load tools
module load mongodb/4.4.1


mongo $BIFROST_DB_KEY <<EOF
db
db.samples.find({"name":/$runname/},{"name":1}).pretty()
db.runs.find({"name":/$runname/},{"name":1}).pretty()
db.sample_components.find({"name":/$runname/},{"name":1}).pretty()
EOF

#echo rm -r $runpath
