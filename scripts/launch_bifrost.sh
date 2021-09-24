#!/bin/bash 
#PBS -A fvst_ssi_dtu
#PBS -l nodes=1:ppn=4,mem=12gb,walltime=03:00:00
#PBS -W group_list=fvst_ssi_dtu
#PBS -W x=advres:fvst_ssi_dtu_wiki_fodevarestyrelsen.16

#Load modules in Computerome


BIFROST_INSTITUTION=$1
BIFROST_YEAR=$2
BIFROST_RUN_NAME=$3
BIFROST_SETTINGS_DIR=$4
echo "Config dir:"
echo $BIFROST_SETTINGS_DIR
source $BIFROST_SETTINGS_DIR/env_vars.sh

module load tools
module load $SINGULARITY_VERSION

RUN_PATH=$BIFROST_INSTITUTION/$BIFROST_YEAR/$BIFROST_RUN_NAME
BIFROST_RUN_DIR=$BIFROST_OUTPUT_DIR/$RUN_PATH
BIFROST_READS_DIR=$BIFROST_RAW_DATA_MNT/$RUN_PATH

[ -d $BIFROST_RUN_DIR ] || mkdir -p $BIFROST_RUN_DIR
cd $BIFROST_RUN_DIR
ln -s $BIFROST_READS_DIR samples


module load $ANACONDA_VERSION;

if [[ -f "$BIFROST_READS_DIR/run_metadata.xlsx" && ! -f "$BIFROST_READS_DIR/run_metadata.tsv" ]]
then
    echo "converting run_metadata.xlsx to tsv"
    $BIFROST_SCRIPT_DIR/xlsx2csv/xlsx2csv.py -d 'tab' -f '%d-%m-%y' $BIFROST_READS_DIR/run_metadata.xlsx > $BIFROST_RUN_DIR/run_metadata.tsv;
fi
if [ -f "$BIFROST_READS_DIR/run_metadata.tsv" ]
then
    cp $BIFROST_READS_DIR/run_metadata.tsv $BIFROST_RUN_DIR/run_metadata.tsv;
fi

if [ -f "$BIFROST_RUN_DIR/run_metadata.tsv" ]
then
    echo "cleaning up species names in run_metadata.tsv"
    python3 $BIFROST_SCRIPT_DIR/change_species.py -meta $BIFROST_RUN_DIR/run_metadata.tsv -out $BIFROST_RUN_DIR/run_metadata.clean.tsv
else
    echo "$BIFROST_RUN_DIR/run_metadata.tsv not found! Exiting!"
    exit
fi

module unload $ANACONDA_VERSION;

#cd /home/projects/ssi_disease_surveillance/data/test_script/bifrost_test_data
# Cleanup from last attempt
# rm run_script.sh
# rm -dr S1
# rm run.yaml
# rm samples.yaml



singularity run \
    -B $BIFROST_RUN_DIR,\
$BIFROST_SCRIPT_DIR:$BIFROST_SCRIPT_DIR:ro,\
$BIFROST_SETTINGS_DIR:$BIFROST_SETTINGS_DIR:ro,\
$BIFROST_LOG_DIR,\
$BIFROST_READS_DIR \
    --userns \
    $BIFROST_IMAGE_DIR/$BIFROST_RUN_LAUNCHER \
        -pre $BIFROST_SCRIPT_DIR/launcher_scripts/pre.sh \
        -per $BIFROST_SCRIPT_DIR/launcher_scripts/per.sh \
        -post $BIFROST_SCRIPT_DIR/launcher_scripts/post.sh \
        -colmap $BIFROST_SETTINGS_DIR/colmap.json \
        -reads $BIFROST_RUN_DIR/samples \
        -meta $BIFROST_RUN_DIR/run_metadata.clean.tsv \
        -name $BIFROST_RUN_NAME \
        -out $BIFROST_RUN_DIR \

bash run_script.sh
