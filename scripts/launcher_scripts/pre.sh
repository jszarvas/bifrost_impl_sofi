# KMA specific config

# General config
export BIFROST_PIPELINE_TOOLS="${BIFROST_PIPELINE_TOOLS:-$BIFROST_IMAGE_DIR}"
export BIFROST_OUTPUT_DIR="${BIFROST_OUTPUT_DIR:-.}"

# Running the following to get 1 id in SAMPLE_PIPELINE_ID for per sample script
unset BIFROST_SAMPLE_START_ID
unset BIFROST_SAMPLE_JOB_IDS
BIFROST_SAMPLE_START_ID=$(echo \
"echo Run started" | \
qsub \
-A $BIFROST_JOB_ACCOUNT \
-h \
-N "bf_$run.name" \
-d $PWD \
-l nodes=1:ppn=1,mem=1gb,walltime=$BIFROST_JOB_TIME \
-W x=advres:$BIFROST_RESNODES
);
BIFROST_SAMPLE_JOB_IDS=$BIFROST_SAMPLE_START_ID
echo "BIFROST_SAMPLE_JOB_IDS: $BIFROST_SAMPLE_JOB_IDS"

