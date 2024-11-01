#!/bin/bash
#PBS -A fvst_ssi_dtu
#PBS -l nodes=1:ppn=4,mem=1gb,walltime=01:00:00
#PBS -W group_list=fvst_ssi_dtu
#PBS -W x=advres:fvst_ssi_dtu_wiki_fodevarestyrelsen.16

module load tools
module load mongodb/4.4.1

collection="samples"
unique_field="categories.sample_info.summary.sofi_sequence_id"

mongo $BIFROST_DB_KEY <<EOF
const latestDocs = db.$collection.aggregate([
  {
    \$sort: { "$unique_field": 1, createdAt: -1 } 
  },
  {
    \$group: {
      _id: "\$$unique_field",
      latestDocId: { \$first: "\$_id" } // Keep the ID of the latest document for each unique field value
    }
  }
])
const latestDocIds = [];
latestDocs.forEach(doc => {latestDocIds.push(doc.latestDocId)});
db.$collection.find({ _id: { \$nin: latestDocIds } });
print(latestDocIds)
EOF
