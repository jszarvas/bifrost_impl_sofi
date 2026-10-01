import os
import yaml
import subprocess
import argparse
from typing import List, Dict
import pandas as pd
from itertools import zip_longest
from time import sleep

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

def prepare_qsub_script(conda_env: str,component_name: str,sample_name,in_dir: str,out_dir: str, runlauncher_args: str, qsub_res: dict, previous_job: str, dryrun: bool = False)->str:

    # Check if in_dir exists
    if not os.path.exists(in_dir):
        raise FileNotFoundError(f"Input directory '{in_dir}' does not exist.")
    
    # Ensure out_dir exists or create it
    os.makedirs(out_dir, exist_ok=True)
    print(f"Output directory '{out_dir}' is ready.")

    job_dependency = ""
    if previous_job != "0":
        job_dependency = f"\n#PBS -W depend=afterany:{previous_job}"

    #Define job name and path
    suffix = ""
    if component_name == "bifrost_run_launcher" and runlauncher_args.find("--finish") > -1:
        suffix = "_fin"
    job_name = f"{conda_env}_{sample_name}{suffix}"
    
    print(f"{sample_name} is run with conda environment {conda_env} for component {component_name}")
    print(f"job name is {job_name}")

    runlauncher_cmd = f"""eval "$(conda shell.bash hook)"\n
cd {os.environ['BASE_DIR']}\n
. settings/env_vars.sh\n
cd {in_dir}\n
conda activate {conda_env}\n
python -m {component_name} --re_run --sample_subset {sample_name.split("___")[1]} --outdir {os.path.dirname(out_dir)} {runlauncher_args} \n
conda deactivate\n"""

    component_odir=f"{component_name.replace('bifrost_', '')}__{conda_env.split('_')[-1]}"
    component_cmd = f"""eval "$(conda shell.bash hook)"\n
cd {os.environ['BASE_DIR']}\n
. settings/env_vars.sh\n
cd {in_dir}\n
conda activate {conda_env}\n
find {out_dir} -wholename "{out_dir}/{component_odir}/runtime_set" -delete\n
find {out_dir} -wholename "{out_dir}/{component_odir}/datadump_complete" -delete\n
python -m {component_name} --sample_name {sample_name} --outdir {out_dir}\n
conda deactivate\n"""

    # arguments to run_launcher
    Bifrost_module_cmd = component_cmd
    if component_name == "bifrost_run_launcher":
        Bifrost_module_cmd = runlauncher_cmd

    #print(f"python module command is \n {Bifrost_module_cmd}")
    
    qsub_job_cmd = f"""#!/bin/bash
#PBS -N {job_name}
#PBS -W x=advres:{os.environ['BIFROST_RESNODES']}{job_dependency}
#PBS -W umask=002
#PBS -W group_list={os.environ['BIFROST_JOB_ACCOUNT']}
#PBS -A {os.environ['BIFROST_JOB_ACCOUNT']}
#PBS -d {out_dir}
#PBS -v {os.environ['QSUB_KEEP_VARS']}
#PBS -l nodes={qsub_res['nodes']}:ppn={qsub_res['ppn']},mem={qsub_res['memory']},walltime={qsub_res['walltime']}
#PBS -o {out_dir}
#PBS -e {out_dir}\n
set -euo pipefail\n
{Bifrost_module_cmd}"""

    pbsjob_id = "0"
    if dryrun == False:
        #sleep at each
        sleep(0.25)
        #Save the job script to a file
        job_script_path = f"{out_dir}/job_{job_name}.pbs"
        with open(job_script_path, "w") as job_script_file:
            job_script_file.write(f"{qsub_job_cmd}")

        print(f"Submitting PBS job script: {job_script_path}")
        try:
            p = subprocess.run(["qsub", job_script_path], check=True, capture_output=True, text=True)
            pbsjob_id = p.stdout.strip()
        except subprocess.CalledProcessError as e:
            print(f"[Error] {e.returncode}: {e.cmd}")
    else:
        print(qsub_job_cmd)
        print("--------------------------------")

    return pbsjob_id

def main(config_file: str, continue_from: str | None, dryrun: bool=False) -> None:
    """
    Main function to load the config, validate environment variables, and submit jobs.
    """

    # Set flag as to it should continue from a given sample
    skip_samples = False
    if continue_from is not None:
        skip_samples = True

    # Check required environment variables
    #required_env_vars = ["BIFROST_DB_KEY","BIFROST_INSTALL_DIR","BIFROST_OUTPUT_DIR", "BIFROST_INSTITUTION", "BIFROST_YEAR", "CONDA_VERSION"]
    required_env_vars = ["BIFROST_DB_KEY","BIFROST_INSTALL_DIR","BIFROST_OUTPUT_DIR","BIFROST_ASM_OUTPUT_DIR","BIFROST_STAGE","BIFROST_RESNODES","QSUB_KEEP_VARS"]
   
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
    runmodes = config["run_mode"]

    bifrost_outdir: Dict[str] = {}
    if len(samples) == len(runmodes):
        for sample, rmode in zip(samples, runmodes):
            if rmode == "SEQ":
                bifrost_outdir[sample] = str(os.environ['BIFROST_OUTPUT_DIR'])
            else:
                bifrost_outdir[sample] = str(os.environ['BIFROST_ASM_OUTPUT_DIR'])
    else:
        # default to SEQ
        bifrost_outdir = {s: str(os.environ['BIFROST_OUTPUT_DIR']) for s in samples}

    pbsjob_ids = {x: ["0"] for x in samples}

    run_launcher_args: Dict[str] = {}
    if "bifrost_run_launcher" in components:
        i = components.index("bifrost_run_launcher")
        component = components.pop(i)
        conda_env = conda_envs.pop(i)
        selected_components = ",".join([f"bifrost_{'_'.join(x.split('_')[2:])}" for x in conda_envs])
        components = [component] + components + [component]
        conda_envs = [conda_env] + conda_envs + [conda_env]

        run_launcher_args = {x: f" --run_mode {rmode} --component_subset {selected_components} --re_run_components" for x, rmode in zip_longest(samples, runmodes, fillvalue=runmodes[0])}

    if len(samples) == len(years): #sample specific years - e.g. 2022,2024
        for sample,runname,year,institution in zip_longest(samples,runnames,years,institutions, fillvalue=institutions[0]): #ensure accurate pairing between sample specific information
            if sample == continue_from:
                skip_samples = False
            if skip_samples:
                print(f"[Skipping] {sample}")
            else:
                print(f"[Processing] {sample}")
                for component, conda_env in zip(components, conda_envs):
                    workdir = os.path.join(bifrost_outdir[sample],institution,year,runname)
                    print(f"workdir as {workdir}")
                    output_dir = os.path.join(workdir,sample)
                    print(f"outdir as {output_dir}")
                    pbsjob_ids[sample].append(prepare_qsub_script(conda_env,component,sample,workdir,output_dir,run_launcher_args[sample],resources,pbsjob_ids[sample][-1],dryrun))
                    if component == "bifrost_run_launcher":
                        run_launcher_args[sample] = run_launcher_args[sample].replace("--re_run_components", "--finish")
    else: #samples from same year
        year = years[0]
        print(f"Year is {year}")
        #potentially different institutions
        for sample,runname,year,institution in zip_longest(samples,runnames,years,institutions, fillvalue=institutions[0]):
            if sample == continue_from:
                skip_samples = False
            if skip_samples:
                print(f"[Skipping] {sample}")
            else:
                print(f"[Processing] {sample}")
                for component, conda_env in zip(components, conda_envs):
                    workdir = os.path.join(bifrost_outdir[sample],institution,year)
                    print(f"workdir as {workdir}")
                    output_dir = os.path.join(workdir,runname)
                    print(f"outdir as {output_dir}")
                    pbsjob_ids[sample].append(prepare_qsub_script(conda_env,component,sample,workdir,output_dir,run_launcher_args[sample],resources,pbsjob_ids[sample][-1],dryrun))
                    if component == "bifrost_run_launcher":
                            run_launcher_args[sample] = run_launcher_args[sample].replace("--re_run_components", "--finish")

if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(description="Run Bifrost pipeline.")

    parser.add_argument("--config_file", type=str, help="Path to the YAML configuration file.")
    parser.add_argument("--continued", type=str, help="Continue submitting jobs from this sample (including it)")
    parser.add_argument("--dryrun", action="store_true", help="Submits the generated PBS files for execution.")

    args = parser.parse_args()

    main(args.config_file, args.continued, args.dryrun)
