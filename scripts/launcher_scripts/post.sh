# Post-script example
# BIFROST_JOB_MEM is set in Prescript
# BIFROST_JOB_CPUS is set in Prescript 
# BIFROST_JOB_PARTITION is set in Prescript
# SAMPLE_JOB_IDS is set in Prescript

# BIFROST_INSTITUTION inherited from bifrost_launcher.sh

LOG_FILE="bifrost_post_sh.log"

log_message() {
    local message="$1"
    local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    echo "[$timestamp] $message" | tee -a "$LOG_FILE"
}

log_message "Starting post-processing script for run $run.name"

log_message "Finalizing statuses for run $run.name with run_launcher"

CONDA_ENV_NAME=bifrost_${BIFROST_STAGE}_${BIFROST_RUN_LAUNCHER/bifrost_/}
COMPONENT_NAME=${BIFROST_RUN_LAUNCHER%_v*}

finish_command=$(echo 'echo "[INFO] run_launcher with RUN '$run.name'" | tee -a '$LOG_FILE';' \
    'module load tools;' \
    'module load '$CONDA_VERSION';' \
    'eval "$(conda shell.bash hook)";' \
    'conda activate "'$CONDA_ENV_NAME'";' \
    'umask 0002;' \
    'python -m "'$COMPONENT_NAME'" --outdir $PWD --run_type '$run.type' --component_subset '$run.component_subset' --finish > complete.txt;')

echo $finish_command >> $LOG_FILE #> command.txt

# Ensure necessary variables are inherited from the prescript
log_message "Using BIFROST_JOB_MEM: $BIFROST_JOB_MEM"
log_message "Using BIFROST_JOB_CPUS: $BIFROST_JOB_CPUS"
log_message "Using BIFROST_JOB_PARTITION: $BIFROST_JOB_PARTITION"
log_message "Using BIFROST_SAMPLE_JOB_IDS: $BIFROST_SAMPLE_JOB_IDS"
log_message "Using BIFROST_INSTITUTION: $BIFROST_INSTITUTION"

recipient_var=BIFROST_RECIPIENTS_$BIFROST_INSTITUTION

log_message "Notification recipients variable: $recipient_var"

last_job_id=$(\
echo $finish_command | \
qsub \
-v QSUB_KEEP_VARS=$QSUB_KEEP_VARS \
-W x=advres:$BIFROST_RESNODES \
-W depend=afterany:$BIFROST_SAMPLE_JOB_IDS \
-W umask=002 \
-A $BIFROST_JOB_ACCOUNT \
-N "post_$run.name" \
-d $PWD \
-l nodes=g-05-c0359:ppn=$BIFROST_JOB_CPUS,mem=$BIFROST_JOB_MEM,walltime=$BIFROST_JOB_TIME \
-m e -M ${!recipient_var}\
)

qrls $BIFROST_SAMPLE_START_ID;

log_message "Released initial job ID: $BIFROST_SAMPLE_START_ID"
