# Logging Configuration
LOG_FILE="bifrost_per_sh.log"

log_message() {
    local message="$1"
    local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    echo "[$timestamp] $message" | tee -a "$LOG_FILE"
}

log_message "Starting per-sample processing for $sample.name from run $run.name"

# Per sample script example
echo "Running $sample.name from $run.name";

SAMPLE=$sample.name;

mkdir $SAMPLE;
pushd $SAMPLE;

# First job is dependant on start, second job on first job and so on
SAMPLE_PIPELINE_ID=$BIFROST_SAMPLE_START_ID

for PIPELINE in $BIFROST_COMPONENTS; do
    log_message "Processing pipeline component: $PIPELINE"
    log_message "Current SAMPLE_PIPELINE_ID: $SAMPLE_PIPELINE_ID"
    
    SAMPLE_PIPELINE_ID=$(submit_sample_component $SAMPLE $PIPELINE $SAMPLE_PIPELINE_ID $sample.name);

    echo "BIFROST_SAMPLE_JOB_IDS: $BIFROST_SAMPLE_JOB_IDS"

done;
popd;

# Add last job id to the list.
BIFROST_SAMPLE_JOB_IDS=$BIFROST_SAMPLE_JOB_IDS:$SAMPLE_PIPELINE_ID;
#echo "BIFROST_SAMPLE_JOB_IDS: $BIFROST_SAMPLE_JOB_IDS"
log_message "Final BIFROST_SAMPLE_JOB_IDS: $BIFROST_SAMPLE_JOB_IDS"
