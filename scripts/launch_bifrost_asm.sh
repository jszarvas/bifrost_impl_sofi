#!/bin/bash 
#PBS -A fvst_ssi_dtu
#PBS -l nodes=1:ppn=4,mem=12gb,walltime=03:00:00
#PBS -W group_list=fvst_ssi_dtu
#PBS -W x=advres:fvst_ssi_dtu_wiki_fodevarestyrelsen.16

#Load modules in Computerome

set -euo pipefail

export BIFROST_INSTITUTION=${1:-}
BIFROST_YEAR=${2:-}
BIFROST_RUN_NAME=${3:-}
BIFROST_SETTINGS_DIR=${4:-}
echo "Config dir:"

source $BIFROST_SETTINGS_DIR/env_vars.sh

module load tools
module load $SINGULARITY_VERSION

RUN_PATH=$BIFROST_INSTITUTION/$BIFROST_YEAR/$BIFROST_RUN_NAME
BIFROST_ASM_RUN_DIR=$BIFROST_ASM_OUTPUT_DIR/$RUN_PATH
BIFROST_ASM_DIR=$BIFROST_ASM_DATA_MNT/$RUN_PATH

if [[ ! -f "$BIFROST_ASM_DIR/sofi_metadata.xlsx" && ! -f "$BIFROST_ASM_DIR/sofi_metadata.tsv" ]]
then
    echo "No sofi_metadata[.xlsx|.tsv] found. Skipping run."
    exit
fi

#Set umask to allow writes by group (should be fvst_admins) and deny writes by all (fvst_ssi_dtu)
umask 0002

[ -d $BIFROST_ASM_RUN_DIR ] || mkdir -p $BIFROST_ASM_RUN_DIR
cd $BIFROST_ASM_RUN_DIR
ln -s $BIFROST_ASM_DIR samples


module load $CONDA_VERSION;
source $BIFROST_CONDA_PATH/conda_init.sh
$CONDACMD activate bifrost_base

if [[ -f "$BIFROST_ASM_DIR/sofi_metadata.xlsx" && ! -f "$BIFROST_ASM_DIR/sofi_metadata.tsv" ]]
then
    echo "converting sofi_metadata.xlsx to tsv"
    $BIFROST_SCRIPT_DIR/xlsx2csv/xlsx2csv.py -d 'tab' -f '%d-%m-%y' $BIFROST_ASM_DIR/sofi_metadata.xlsx > $BIFROST_ASM_RUN_DIR/sofi_metadata.tsv;
fi
if [ -f "$BIFROST_ASM_DIR/sofi_metadata.tsv" ]
then
    echo "copying sofi_metadata.tsv to run_dir"
    cp $BIFROST_ASM_DIR/sofi_metadata.tsv $BIFROST_ASM_DIR/sofi_metadata.tsv;
fi

if [ -f "$BIFROST_ASM_DIR/sofi_metadata.tsv" ]
then
    echo "cleaning up species names in sofi_metadata.tsv"
    python3 $BIFROST_SCRIPT_DIR/change_species.py -meta $BIFROST_ASM_DIR/sofi_metadata.tsv -out $BIFROST_ASM_RUN_DIR/sofi_metadata.clean.tsv
else
    echo "$BIFROST_RUN_DIR/sofi_metadata.tsv not found! Exiting!"
    exit
fi

$CONDACMD deactivate

## Start run_launcher conda


COMPONENT=$BIFROST_RUN_LAUNCHER
COMPONENT_VERSION=v${COMPONENT##*_v}
COMPONENT_NAME=${COMPONENT%_v*}
COMPONENT_CLEAN_NAME=${COMPONENT_NAME#bifrost_}
STAGE=${BIFROST_STAGE:+${BIFROST_STAGE}_}

$CONDACMD activate bifrost_$STAGE${COMPONENT_CLEAN_NAME}_$COMPONENT_VERSION

python -m $COMPONENT_NAME \
        -rerun \
        -pre $BIFROST_SCRIPT_DIR/launcher_scripts/pre.sh \
        -per $BIFROST_SCRIPT_DIR/launcher_scripts/per.sh \
        -post $BIFROST_SCRIPT_DIR/launcher_scripts/post.sh \
        -colmap $BIFROST_SETTINGS_DIR/colmap.json \
        -reads $BIFROST_ASM_RUN_DIR/samples \
        -meta $BIFROST_ASM_RUN_DIR/sofi_metadata.clean.tsv \
        -name $BIFROST_RUN_NAME \
        -out $BIFROST_ASM_RUN_DIR;

$CONDACMD deactivate

module unload $CONDA_VERSION;

#bash run_script.sh
