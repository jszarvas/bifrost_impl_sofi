#!/usr/bin/bash
umask 002

if [ "x$BASE_DIR" == "x" ]; then
    echo "\$BASE_DIR not set. Exiting"
    exit
fi

source $BASE_DIR/settings/env_vars.sh
LOG="$BIFROST_LOG_DIR/cron_run.log"
cd $BIFROST_SCRIPT_DIR
echo ""
echo -n "cron_run.sh starting ($USER)" | tee -a $LOG
date | tee -a $LOG
source /etc/bashrc | tee -a $LOG
python3 utils/clean_up_runs.py 2>&1 | tee -a $LOG
python3 utils/rerun_samples.py 2>&1 | tee -a $LOG
bash $BIFROST_SCRIPT_DIR/start.sh 2>&1 | tee -a $LOG
#python3 utils/fix_output_permissions.py 2>&1 | tee -a $LOG

