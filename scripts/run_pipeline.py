import os
import yaml
import subprocess
import argparse
from typing import List, Dict

def load_config(config_file: str) -> Dict:
    """Load the YAML configuration file."""
    with open(config_file, "r") as file:
        return yaml.safe_load(file)

def check_environment_variables(required_vars: List[str], print_val: bool = False) -> None:
    """Ensure required environment variables are set."""
    missing_vars = [var for var in required_vars if var not in os.environ]
    if missing_vars:
        raise EnvironmentError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    if print_val == True:
        for var in required_vars:
            print(f"environment {var} is {os.environ[var]}")

def check_conda_environment(required_envs: List[str]) -> None:
    # Parse available Conda environments
    available_envs = [
        line.split()[0]
        for line in subprocess.run(
                ["conda", "env", "list"], stdout=subprocess.PIPE, text=True).stdout.splitlines()
        if line and not line.startswith("#")
    ]
    
    # Find missing environments
    missing_envs = [env for env in required_envs if env not in available_envs]
    
    # Output results
    if missing_envs:
        raise ValueError(f"Missing Conda environments: {missing_envs}")
    else:
        print("All required Conda environments are present.")

def construct_output_path(sample_name: str):
    """
    Construct the output path for the given sample using environment variables.
    """
    bifrost_output_dir = os.environ["BIFROST_OUTPUT_DIR"]
    bifrost_institution = os.environ["BIFROST_INSTITUTION"]
    bifrost_year = os.environ["BIFROST_YEAR"]
    # Assuming the sample name corresponds to the run name
    run_name = sample_name
    
    return os.path.join(bifrost_output_dir, bifrost_institution, bifrost_year, run_name)

def prepare_qsub_script(conda_env: str,component_name: str,sample_name,in_dir: str,out_dir: str,qsub_res: dict, run: bool = False)->str:

    # Check if in_dir exists
    if not os.path.exists(in_dir):
        raise FileNotFoundError(f"Input directory '{in_dir}' does not exist.")
        print(f"Input directory '{in_dir}' exists.")
    
    # Ensure out_dir exists or create it
    os.makedirs(out_dir, exist_ok=True)
    print(f"Output directory '{out_dir}' is ready.")
 
    #Define job name and path
    job_name = f"{component_name}_{conda_env}_{sample_name}"
    
    print(f"{sample_name} is run with conda environment {conda_env} for component {component_name}")
    print(f"job name is {job_name}")

#module load tools
#module load {os.environ['CONDA_VERSION']}\
    Bifrost_module_cmd = f"""eval "$(conda shell.bash hook)"\n
cd /home/projects/fvst_ssi_dtu/{os.environ['BIFROST_STAGE']}_app\n
. settings/env_vars.sh\n
cd {in_dir}\n
conda activate {conda_env}\n
python -m {component_name} --sample_name {sample_name} --outdir {out_dir}\n
conda deactivate\n"""

    #print(f"python module command is \n {Bifrost_module_cmd}")
    
    qsub_job_cmd = f"""#!/bin/bash
#PBS -N {job_name}
#PBS -W x=advres:{os.environ['BIFROST_RESNODES']}
#PBS -W umask=002
#PBS -d {out_dir}
#PBS -v {os.environ['QSUB_KEEP_VARS']}
#PBS -l nodes={qsub_res['nodes']}:ppn={qsub_res['ppn']},mem={qsub_res['memory']},walltime={qsub_res['walltime']}
#PBS -o {out_dir}/{job_name}.out
#PBS -e {out_dir}/{job_name}.err\n
{Bifrost_module_cmd}"""

    # create qsub script
    
    #Save the job script to a file
    job_script_path = f"{out_dir}/job_{job_name}.pbs"
    with open(job_script_path, "w") as job_script_file:
        job_script_file.write(f"{qsub_job_cmd}")

    if run == False:
        print(f"Submitting PBS job script: {job_script_path}")
        subprocess.run(["qsub", job_script_path], check=True)

    return job_script_path

def main(config_file: str, run: bool=False) -> None:
    """
    Main function to load the config, validate environment variables, and submit jobs.
    """

    # Check required environment variables
    #required_env_vars = ["BIFROST_DB_KEY","BIFROST_INSTALL_DIR","BIFROST_OUTPUT_DIR", "BIFROST_INSTITUTION", "BIFROST_YEAR", "CONDA_VERSION"]
    required_env_vars = ["BIFROST_DB_KEY","BIFROST_INSTALL_DIR","BIFROST_OUTPUT_DIR","BIFROST_STAGE","BIFROST_RESNODES","QSUB_KEEP_VARS"]
   
    check_environment_variables(required_env_vars,True)

    # Load configuration
    config = load_config(config_file)
    
    #Extract configurations
    components = config["component_names"]
    conda_envs = config["conda_envs"]

    check_conda_environment(conda_envs)

    print(conda_envs)
    samples = config["sample_names"]

    # Verify the number of components matches the number of Conda environments
    if len(components) != len(conda_envs):
        raise ValueError("The number of component names: {components} must match the number of conda environments: {conda_envs}.")
            
    #Extract qsub resources
    resources = config["resources"]
    required_resource_keys = ["nodes", "ppn", "memory", "walltime"]
    
    #Extract python module specific information - for directory information
    institutions = config["institution"]
    years = config["year"]
    runnames = config["runname"]
    
    print("length ",len(years))
    for institution,year,runname in zip(institutions,years,runnames):
        print(f"test : {institution}/{year}/{runname}")

    bifrost_outdir = str(os.environ['BIFROST_OUTPUT_DIR'])
    print(f"bifrost_outdir {bifrost_outdir}")

    for component, conda_env in zip(components, conda_envs):
        if len(samples) == len(years): #sample specific years - e.g. 2022,2024
            if len(samples) == len(institutions): #sample specific institutions - e.g. ssi,fvst
                for sample,runname,year,institution in zip(samples,runnames,years,institutions): #ensure accurate pairing between sample specific information
                    workdir = os.path.join(bifrost_outdir,institution,year,runname)
                    print(f"workdir 1 works as {workdir}")
                    output_dir = os.path.join(workdir,sample)
                    print(f"outdir 1 works as {output_dir}")
                    prepare_qsub_script(conda_env,component,sample,workdir,output_dir,resources,run)
            else:
                for sample,runname,year in zip(samples,runnames,years): #samples from same institutions
                    institution = institutions[0]
                    workdir = os.path.join(bifrost_outdir,institution,year)
                    print(f"workdir 2 works as {workdir}")
                    output_dir = os.path.join(workdir,runname)
                    print(f"outdir 2 works as {output_dir}")
                    prepare_qsub_script(conda_env,component,sample,workdir,output_dir,resources,run)
        else: #samples from same year
            year = years[0]
            for sample in samples:
                if len(samples) == len(institutions): #potentially different institutions
                    for sample,runname,institution in zip(samples,runnames,institutions):
                        workdir = os.path.join(bifrost_outdir,institution,year)
                        print(f"workdir 3 works as {workdir}")
                        output_dir = os.path.join(workdir,runname)
                        print(f"outdir 3 works as {output_dir}")
                        prepare_qsub_script(conda_env,component,sample,workdir,output_dir,resources,run)
                else:
                    for sample,runname in zip(samples,runnames):
                        institution = institutions[0]
                        workdir = os.path.join(bifrost_outdir,institution,year)
                        print(f"workdir 4 works as {workdir}")
                        output_dir = os.path.join(workdir,runname)
                        print(f"outdir 4 works as {output_dir}")
                        prepare_qsub_script(conda_env,component,sample,workdir,output_dir,resources,run)

if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(description="Run Bifrost pipeline.")

    parser.add_argument("--config_file", type=str, help="Path to the YAML configuration file.")
    parser.add_argument("--dryrun", action="store_true", help="Submits the generated PBS files for execution.")

    args = parser.parse_args()

    main(args.config_file,args.dryrun)
