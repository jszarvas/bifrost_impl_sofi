#!/usr/bin/bash

set -euo pipefail

source /home/projects/fvst_ssi_dtu/prod_app/settings/env_vars.sh

umask 002

source $BASE_DIR/settings/env_vars.sh
LOG="$BIFROST_LOG_DIR/cron_run.log"
cd $BIFROST_SCRIPT_DIR
echo "" | tee -a $LOG
echo -n "cron_run.sh starting ($USER@$HOSTNAME) " | tee -a $LOG
date | tee -a $LOG
set +u
source /etc/bashrc | tee -a $LOG
set -u
## Load git settings
bash ../settings/git_settings.sh
#bash -l -c "utils/mailer.sh utils/mailer/run_complete_message.txt utils/mailer/ssi_recipients.txt 2>&1 | tee -a $LOG"
echo "Cleaning" | tee -a $LOG
#python3 utils/clean_up_runs.py 2>&1 | tee -a $LOG
echo "Re-run samples" | tee -a $LOG
#python3 utils/rerun_samples.py 2>&1 | tee -a $LOG
echo "Processing samples" | tee -a $LOG
source ../settings/env_vars.sh
python3 $BIFROST_SCRIPT_DIR/check_and_launch_runs.py;
#bash $BIFROST_SCRIPT_DIR/start.sh 2>&1 | tee -a $LOG
#python3 utils/fix_output_permissions.py 2>&1 | tee -a $LOG

