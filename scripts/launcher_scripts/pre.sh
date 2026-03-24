
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

  local command=$(echo 'echo "[INFO] submit_sample_component with SAMPLE '$SAMPLE' for component '$COMPONENT' for sample_name '$sample_name'" | tee -a '$LOG_FILE';' \
      'module load tools;' \
      'module load '$CONDA_VERSION';' \
      'eval "$(conda shell.bash hook)";' \
      'conda activate "'$CONDA_ENV_NAME'";' \
      'python -m "'$COMPONENT_NAME'" --sample_name "'$sample_name'" ;')
  
  echo $command >> $LOG_FILE #> command.txt

  #echo $command | tee -a $LOG_FILE

  SAMPLE_PIPELINE_ID=$(\
    echo $command | \
    qsub \
      -v sample_name="$sample_name",QSUB_KEEP_VARS=$QSUB_KEEP_VARS \
      -d $PWD \
      -A $BIFROST_JOB_ACCOUNT \
      -W depend=afterany:$PREVIOUS_ID \
      -W umask=002 \
      -N "${SAMPLE}_${COMPONENT_NAME}_bf" \
      -W x=advres:$BIFROST_RESNODES \
      -l nodes=1:ppn=$cpus,mem=$mem,walltime=$time \
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

BIFROST_SAMPLE_START_ID=$(echo \
"echo Run started" | \
qsub \
-A $BIFROST_JOB_ACCOUNT \
-h \
-N "bf_$run.name" \
-d $PWD \
-l nodes=1:ppn=1,mem=1gb,walltime=$BIFROST_JOB_TIME \
-W x=advres:$BIFROST_RESNODES \
-W umask=002
);

log_message "Initial job submitted with ID: $BIFROST_SAMPLE_START_ID"
BIFROST_SAMPLE_JOB_IDS=$BIFROST_SAMPLE_START_ID
echo "BIFROST_SAMPLE_JOB_IDS: $BIFROST_SAMPLE_JOB_IDS"

log_message "BIFROST_SAMPLE_JOB_IDS: $BIFROST_SAMPLE_JOB_IDS"
