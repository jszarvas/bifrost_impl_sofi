#!/usr/bin/bash

source /home/projects/fvst_ssi_dtu/test_app/settings/env_vars.sh
LOG="$BIFROST_LOG_DIR/cron_run.log"
cd $BIFROST_SCRIPT_DIR
echo -n "Cron_run starting ($USER)" | tee -a $LOG
date | tee -a $LOG
source /etc/bashrc | tee -a $LOG
bash $BIFROST_SCRIPT_DIR/start.sh 2>&1 | tee -a $LOG
