#!/bin/bash 

runpath=$1
runname=`basename $runpath`

echo $runname

mongosh $BIFROST_DB_KEY <<EOF
db
db.samples.deleteMany({"name":/$runname/})
db.runs.deleteMany({"name":/$runname/})
db.sample_components.deleteMany({"name":/$runname/})
EOF

