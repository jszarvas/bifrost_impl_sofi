#!/bin/bash 
#PBS -A fvst_ssi_dtu
#PBS -l nodes=1:ppn=4,mem=12gb,walltime=03:00:00
#PBS -W group_list=fvst_ssi_dtu
#PBS -v BIFROST_SETTINGS_DIR
#PBS -W x=advres:fvst_ssi_dtu_wiki_fodevarestyrelsen.16
#PBS -W umask=0002

#Load modules in Computerome


BIFROST_INSTITUTION=$1
BIFROST_YEAR=$2
BIFROST_RUN_NAME=$3
BIFROST_SAMPLES_TO_RERUN=$4 
#BIFROST_RUN_ID=$4
#BIFROST_SAMPLES_TO_RERUN=$5 
#BIFROST_SETTINGS_DIR=$6

echo "Config dir:"
echo $BIFROST_SETTINGS_DIR
source $BIFROST_SETTINGS_DIR/env_vars.sh

module load tools
module load $SINGULARITY_VERSION

RUN_PATH=$BIFROST_INSTITUTION/$BIFROST_YEAR/$BIFROST_RUN_NAME
BIFROST_RUN_DIR=$BIFROST_OUTPUT_DIR/$RUN_PATH
BIFROST_READS_DIR=$BIFROST_RAW_DATA_MNT/$RUN_PATH

if [[ ! -f "$BIFROST_READS_DIR/sofi_metadata.xlsx" && ! -f "$BIFROST_READS_DIR/sofi_metadata.tsv" ]]
then
    echo "No sofi_metadata[.xlsx|.tsv] found. Skipping run."
    exit
fi

#Set umask to allow writes by group (should be fvst_admins) and deny writes by all (fvst_ssi_dtu)
umask 0002

[ -d $BIFROST_RUN_DIR ] || mkdir -p $BIFROST_RUN_DIR
cd $BIFROST_RUN_DIR
ln -s $BIFROST_READS_DIR samples


module load $CONDA_VERSION;

if [[ -f "$BIFROST_READS_DIR/sofi_metadata.xlsx" && ! -f "$BIFROST_READS_DIR/sofi_metadata.tsv" ]]
then
    echo "converting sofi_metadata.xlsx to tsv"
    $BIFROST_SCRIPT_DIR/xlsx2csv/xlsx2csv.py -d 'tab' -f '%d-%m-%y' $BIFROST_READS_DIR/sofi_metadata.xlsx > $BIFROST_RUN_DIR/sofi_metadata.tsv;
fi
if [ -f "$BIFROST_READS_DIR/sofi_metadata.tsv" ]
then
    echo "copying sofi_metadata.tsv to run_dir"
    cp $BIFROST_READS_DIR/sofi_metadata.tsv $BIFROST_RUN_DIR/sofi_metadata.tsv;
fi

if [ -f "$BIFROST_RUN_DIR/sofi_metadata.tsv" ]
then
    echo "cleaning up species names in sofi_metadata.tsv"
    python3 $BIFROST_SCRIPT_DIR/change_species.py -meta $BIFROST_RUN_DIR/sofi_metadata.tsv -out $BIFROST_RUN_DIR/sofi_metadata.clean.tsv
else
    echo "$BIFROST_RUN_DIR/sofi_metadata.tsv not found! Exiting!"
    exit
fi

module unload $CONDA_VERSION;

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
        -meta $BIFROST_RUN_DIR/sofi_metadata.clean.tsv \
        -name $BIFROST_RUN_NAME \
        -out $BIFROST_RUN_DIR \
        -s $BIFROST_SAMPLES_TO_RERUN;

bash run_script.sh
