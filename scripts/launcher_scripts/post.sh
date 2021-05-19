# Post-script example
# BIFROST_JOB_MEM is set in Prescript
# BIFROST_JOB_CPUS is set in Prescript 
# BIFROST_JOB_PARTITION is set in Prescript
# SAMPLE_JOB_IDS is set in Prescript

echo \
"\
touch complete.txt
 " | \
qsub \
-W x=advres:$BIFROST_RESNODES \
-W depend=afterany:$BIFROST_SAMPLE_JOB_IDS \
-A $BIFROST_JOB_ACCOUNT \
-N "post_$run.name" \
-d $PWD \
-l nodes=1:ppn=$BIFROST_JOB_CPUS,mem=$BIFROST_JOB_MEM,walltime=$BIFROST_JOB_TIME \



qrls $BIFROST_SAMPLE_START_ID;
