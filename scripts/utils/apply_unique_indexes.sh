#!/bin/bash 
#PBS -A fvst_ssi_dtu
#PBS -l nodes=1:ppn=1,mem=1gb,walltime=00:05:00
#PBS -W group_list=fvst_ssi_dtu
#PBS -v BIFROST_DB_KEY
#PBS -W x=advres:fvst_ssi_dtu_wiki_fodevarestyrelsen.16

module load tools
module load mongodb/4.4.1

command="
db.runs.createIndex({ \"name\": 1 },{ unique: true })
db.components.createIndex({ \"name\": 1 },{ unique: true })
db.samples.createIndex({ \"categories.sample_info.summary.sofi_sequence_id\": 1 },{ unique: true })
"

echo "Executing \"$command\" on \"$BIFROST_DB_KEY\""

output=$(echo "$command" | mongo $BIFROST_DB_KEY 2>&1)  # Capture the output and error messages
exit_code=$?
if [[ $exit_code -eq 0 ]]; then
  echo "Command executed successfully."
else
  echo "Command execution failed with exit code $exit_code: $output"
fi


