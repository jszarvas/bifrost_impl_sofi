
# KMA specific config


# Logging Configuration
LOG_FILE="bifrost_pre_sh.log"

log_message() {
    local message="$1"
    local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    echo "[$timestamp] $message" | tee -a "$LOG_FILE"
}

# Utility functions
string_contains() {
  local search="$1"
  local string="$2"

  for element in $string; do
    if [[ "$element" == "$search" ]]; then
      return 0
    fi
  done

  return 1
}

# Error handling
handle_error() {
  local command="$BASH_COMMAND"
  log_message "ERROR: An error occurred while executing: $command"
  echo "An error occurred while executing: $command"
  exit 1
}

# Set the trap to call the exception handling function
trap 'handle_error' ERR

submit_sample_component() {
  local SAMPLE="$1"
  local COMPONENT="$2"
  local PREVIOUS_ID="$3"
  local sample_name="$4"


  local COMPONENT_VERSION=v${COMPONENT##*_v}
  local COMPONENT_NAME=${COMPONENT%_v*}
  local COMPONENT_CLEAN_NAME=${COMPONENT_NAME#bifrost_}
  local STAGE=${BIFROST_STAGE:+${BIFROST_STAGE}_}

  local LOG_FILE="${PWD}/${COMPONENT_CLEAN_NAME}_pre_sh.log"

  
  local cpus=$BIFROST_JOB_CPUS
  local mem=$BIFROST_JOB_MEM
  local time=$BIFROST_JOB_TIME
  
  echo $COMPONENT_CLEAN_NAME $BIG_COMPONENTS >> $LOG_FILE
  if string_contains $COMPONENT_CLEAN_NAME "$BIG_COMPONENTS"; then
      local cpus=$BIFROST_CPUS_BIG
      local mem=$BIFROST_MEM_BIG
  elif string_contains $COMPONENT_CLEAN_NAME "$KRAKEN_COMPONENTS"; then
      local cpus=$BIFROST_CPUS_KRAKEN
      local mem=$BIFROST_MEM_KRAKEN
  fi
  echo cpus=$cpus mem=$mem >> $LOG_FILE
  local CONDA_ENV_NAME=bifrost_${STAGE}${COMPONENT_CLEAN_NAME}_${COMPONENT_VERSION}

  SAMPLE_PIPELINE_ID=$(\
    sbatch \
      -J "${SAMPLE}_${COMPONENT_NAME}_bf" \
      --error "%x.%a.err.log" \
      --output "%x.%a.out.log" \
      --export=sample_name,$BIFROST_KEEP_VARS \
      -D $PWD \
      --parsable \
      --dependency=afterany:$PREVIOUS_ID \
      -A $BIFROST_JOB_ACCOUNT \
      --reservation=$BIFROST_RESNODES \
      --partition=$BIFROST_PARTITION \
      --nodelist="g-01-c0010" \
      --ntasks=$cpus --mem=$mem --time=$time <<EOF
#!/bin/bash

echo "[INFO] submit_sample_component with SAMPLE ${SAMPLE} for component ${COMPONENT} for sample_name ${sample_name}" | tee -a ${LOG_FILE}
module load tools
module load ${CONDA_VERSION}
eval $(conda shell.bash hook)
conda activate ${CONDA_ENV_NAME}
umask 0002
python -m ${COMPONENT_NAME} --sample_name ${sample_name}
EOF
);
  
  #log_message "Sample component job submitted with ID: $SAMPLE_PIPELINE_ID"
  echo $SAMPLE_PIPELINE_ID
  #echo "DEBUG: Before log_message, sample_name=$sample_name" | tee -a "$LOG_FILE"
  #echo "submit_sample_component with $SAMPLE for $COMPONENT with $sample_name" | tee -a "$LOG_FILE"
  #log_message "submit_sample_component with $SAMPLE for $COMPONENT with $sample_name"
  #echo "DEBUG: After log_message, sample_name=$sample_name" | tee -a "$LOG_FILE"
  
}

# General config
export BIFROST_PIPELINE_TOOLS="${BIFROST_PIPELINE_TOOLS:-$BIFROST_IMAGE_DIR}"
export BIFROST_OUTPUT_DIR="${BIFROST_OUTPUT_DIR:-.}"

# Running the following to get 1 id in SAMPLE_PIPELINE_ID for per sample script
unset BIFROST_SAMPLE_START_ID
unset BIFROST_SAMPLE_JOB_IDS

log_message "Initializing sample pipeline job submission"

BIFROST_SAMPLE_START_ID=$(sbatch \
-A $BIFROST_JOB_ACCOUNT \
-H \
-J "bf_$run.name" \
-D $PWD \
--error "%x.%a.err.log" \
--output "%x.%a.out.log" \
--parsable \
--reservation=$BIFROST_RESNODES \
--partition=$BIFROST_PARTITION \
--ntasks=1 --mem=1G --time=$BIFROST_JOB_TIME << EOF
#!/bin/sh
echo Run started
EOF
);

log_message "Initial job submitted with ID: $BIFROST_SAMPLE_START_ID"
BIFROST_SAMPLE_JOB_IDS=$BIFROST_SAMPLE_START_ID
echo "BIFROST_SAMPLE_JOB_IDS: $BIFROST_SAMPLE_JOB_IDS"

log_message "BIFROST_SAMPLE_JOB_IDS: $BIFROST_SAMPLE_JOB_IDS"
