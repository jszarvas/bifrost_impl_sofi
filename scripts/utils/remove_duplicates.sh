#!/bin/bash
#PBS -A fvst_ssi_dtu
#PBS -l nodes=1:ppn=4,mem=1gb,walltime=01:00:00
#PBS -W group_list=fvst_ssi_dtu
#PBS -W x=advres:fvst_ssi_dtu_wiki_fodevarestyrelsen.16

module load tools
module load mongodb/4.4.1



mongo $BIFROST_DB_KEY <<EOF
const latestDocs = db.samples.aggregate([
  {
    $sort: { "categories.sample_info.summary.sofi_sequence_id": 1, createdAt: -1 } // Sort by unique field, then by timestamp descending
  },
  {
    $group: {
      _id: "$categories.sample_info.summary.sofi_sequence_id",
      latestDocId: { $first: "$_id" } // Keep the ID of the latest document for each unique field value
    }
  }
])
const latestDocIds = [];
latestDocs.forEach(doc => {latestDocIds.push(doc.latestDocId)});
db.samples.find({ _id: { $nin: latestDocIds } });
EOF
