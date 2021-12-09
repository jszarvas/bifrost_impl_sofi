# sofi_chewie
chewieSnake for SOFI.

## Prerequisites
chewieSnake must be installed and available as a command. In a dev environment, the
preferred way is by using the Mamba package manager - see chewieSnake install instructions.

Also check out this repo somewhere on your filesystem.

## Basic installation
Copy the folder config.template as a new folder outside of the repo; call it f. ex. 'cs', so 'cp -r config.template ../cs'.
This folder will be the top-level chewieSnake config folder. It will contain species-specific subfolders which
will contain all config specific the that species.

## Config for one species
- cd to the the species-specific subfolder you want to use (for instance, Salmonella_enterica). If the folder
for the species does not exist, create it by copying the Salmonella_enterica subfolder with all its contents.
- For each allele scheme you want to use for this species, download the scheme scheme and place it beneath
cs/(species)/schemes. Some schemes can be found here: https://seafile.bfr.berlin/d/b4a619b12db14c5eab74/
- Edit config.sh so that is has the correct parameters. The file will be read by the
script run_chewiesnake.sh. Check that the parameters are set correctly by running:

source config.sh
echo $SPECIES
echo $SCHEME
echo $PRODIGAL
echo $OUTPUT

## Prepare sample list
maintain_sample_list.py is a script for creating and maintaining sample lists for chewieSnake.
Normally these sample lists will be species-specific, i. e. you will maintain one "global"
sample list for all samples of a specific species. With this list, you can run chewieSnake
for that specific species. Since the list not only contains new samples but also old ones, chewieSnake
will not only calculate distances between new samples but also between old and new ones.

Decide what sequence data input folder you want to run though chewieSnake. It's probably a good idea
to set the path in an envvar ($SEQDATA like in the example below).

Example (running from the same directory as sample_list.tsv):

/path/to/maintain_sample_list.py sample_list.tsv -s Salmonella_enterica -d /path/to/run_folder

It's important to use the -s option option since this will make a list only with samples of the
relevant species. maintain_sample_list.py will look up the species in a file named run_metadata.tsv
in the seqdata folder, so make sure this file is present.

## Run chewieSnake

### Running chewieSnake without HPC job control
Normal run:
- cd /path/to/cs/Salmonella_enterica
- /path/to/run_chewiesnake sample_list.tsv

Note: 'normal run' without running through HPC is only possible in a development
environment, i. e. in an environmment where the envvar DEV_ENV is not set. This is
to prevent a user from accidentally starting a 'real' chewieSnake run without using the
HPC.

'Dry run' (not really running, just simulating):
- cd /path/to/cs/Salmonella_enterica
- /path/to/run_chewiesnake sample_list.tsv --dryrun

Unlock output directory:
'Dry run' (not really running, just simulating):
- cd /path/to/cs/Salmonella_enterica
- /path/to/run_chewiesnake sample_list.tsv --unlock

### Create an HPC job (with Torque)
Normal run:
- cd /path/to/cs/Salmonella_enterica
- qsub -F "sample_list.tsv" run_chewiesnake.sh 

'Dry run' (not really running, just simulating):
- cd /path/to/cs/Salmonella_enterica
- qsub -F "sample_list.tsv --dryrun" run_chewiesnake.sh

Unlock output directory:
- cd /path/to/cs/Salmonella_enterica
- qsub -F "sample_list.tsv --unlock" run_chewiesnake.sh

If you are in an interactive HPC job, you might also use the commands described in
"Running chewieSnake without HPC job control".

Note that the $SCHEME location has to be writeable since chewieSnake will place temporary data in it.
Most importantly, it will place a folder named .lock which indicates that a chewieSnake process is active
using this scheme. This would prevent more chewieSnake processes running on the same data. This lock is
different the one that locks the output directory.
