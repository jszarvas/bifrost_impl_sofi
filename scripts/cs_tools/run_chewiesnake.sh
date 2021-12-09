#!/bin/bash

### Specify group name to resource manager
#PBS -A fvst_ssi_dtu

### Specify group name to resource manager
#PBS -W x=advres:fvst_ssi_dtu_wiki_fodevarestyrelsen.16

### Specify resources
#PBS -l nodes=1:ppn=4,mem=12gb,walltime=30:00:00,advres=fvst_ssi_dtu_wiki_fodevarestyrelsen.16

if [[ -z "${DEV_ENV}" ]]; then
  echo Load chewieSnake from module
  module load tools
  module load chewiesnake/3.0.0

  if [[ -z "${PBS_O_WORKDIR}" && -z $2 ]]; then
    echo PBS_O_WORKDIR set, DEV_ENV not set, and script called without options - exiting.
    exit 1
  fi
fi

# Go to the directory from where the script was called
if [[ $PBS_O_WORKDIR ]]; then
  DIR=$PBS_O_WORKDIR
else
  DIR=$PWD
fi
echo Working directory: $DIR
cd $DIR

# Read parameters from species config
source config.sh
echo Species: $SPECIES
SAMPLE_LIST=$1
echo Sample list: $SAMPLE_LIST
SCHEME=$DIR/schemes/$SCHEME
echo Scheme: $SCHEME
echo Prodigal file: $PRODIGAL
OUTPUT=$DIR/$OUTPUT
echo Output directory: $OUTPUT

cmd="chewiesnake -t 10 --reads \
--sample_list $SAMPLE_LIST \
--scheme $SCHEME \
--prodigal $PRODIGAL \
--working_directory $OUTPUT"

if [ "$2" == "--dryrun" ]; then
 cmd="${cmd} --dryrun"
fi

if [ "$2" == "--unlock" ]; then
 cmd="${cmd} --unlock"
fi

$cmd
