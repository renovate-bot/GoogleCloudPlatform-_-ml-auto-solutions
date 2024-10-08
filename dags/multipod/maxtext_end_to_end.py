# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""A DAG to run end-to-end MaxText tests."""


import datetime
from airflow import models
from dags import composer_env, test_owner
from dags.vm_resource import XpkClusters, CpuVersion, DockerImage, GpuVersion, Project, TpuVersion, Zone
from dags.multipod.configs import gke_config
from airflow.utils.task_group import TaskGroup
from xlml.utils import name_format

# Run once a day at 4 am UTC (8 pm PST)
SCHEDULED_TIME = "0 4 * * *" if composer_env.is_prod_env() else None


with models.DAG(
    dag_id="maxtext_end_to_end",
    schedule=SCHEDULED_TIME,
    tags=["multipod_team", "maxtext", "stable", "nightly"],
    start_date=datetime.datetime(2024, 1, 19),
    catchup=False,
) as dag:
  test_name_prefix = "maxtext"
  test_models_tpu = {
      "llama2-7b": "tpu/llama2/7b/test_llama2_7b",
      "mistral-7b": "tpu/mistral/7b/test_mistral-7b",
      "gemma-2b": "tpu/gemma/2b/test_gemma",
      "gpt3": "tpu/test_gpt3",
  }

  for model, test_script in test_models_tpu.items():
    stable_tpu = gke_config.get_gke_config(
        time_out_in_min=60,
        test_name=f"{test_name_prefix}-stable-{model}",
        run_model_cmds=(f"bash end_to_end/{test_script}.sh",),
        docker_image=DockerImage.MAXTEXT_TPU_JAX_STABLE_STACK.value,
        test_owner=test_owner.JON_B,
    ).run()
    nightly_tpu = gke_config.get_gke_config(
        time_out_in_min=60,
        test_name=f"{test_name_prefix}-nightly-{model}",
        run_model_cmds=(f"bash end_to_end/{test_script}.sh",),
        docker_image=DockerImage.MAXTEXT_TPU_JAX_NIGHTLY.value,
        test_owner=test_owner.JON_B,
    ).run()
    stable_tpu >> nightly_tpu

  multicluster_test_models = {
      "gemma-7b": [
          {
              "script_name": "tpu/gemma/7b/1_test_gemma",
              "cluster": XpkClusters.CPU_N2_STANDARD_64_CLUSTER,
              "time_out_in_min": 60,
          },
          {
              "script_name": "tpu/gemma/7b/2_test_gemma",
              "cluster": XpkClusters.TPU_V4_16_CLUSTER,
              "time_out_in_min": 60,
          },
      ],
      "mixtral-8x7b": [
          {
              "script_name": "tpu/mixtral/8x7b/1_test_mixtral",
              "cluster": XpkClusters.CPU_M1_MEGAMEM_96_CLUSTER,
              "time_out_in_min": 240,
          },
          {
              "script_name": "tpu/mixtral/8x7b/2_test_mixtral",
              "cluster": XpkClusters.TPU_V4_128_CLUSTER,
              "time_out_in_min": 60,
          },
      ],
      "mixtral-8x22b": [
          {
              "script_name": "tpu/mixtral/8x22b/1_test_mixtral",
              "cluster": XpkClusters.CPU_M1_MEGAMEM_96_CLUSTER,
              "time_out_in_min": 360,
          },
          {
              "script_name": "tpu/mixtral/8x22b/2_test_mixtral",
              "cluster": XpkClusters.TPU_V5E_256_CLUSTER,
              "time_out_in_min": 60,
          },
      ],
      "llama2-70b": [
          {
              "script_name": "tpu/llama2/70b/1_test_llama2_70b",
              "cluster": XpkClusters.CPU_M1_MEGAMEM_96_CLUSTER,
              "time_out_in_min": 360,
          },
          {
              "script_name": "tpu/llama2/70b/2_test_llama2_70b",
              "cluster": XpkClusters.TPU_V4_128_CLUSTER,
              "time_out_in_min": 60,
          },
      ],
  }

  for model, test_scripts_details in multicluster_test_models.items():
    gcs_subfolder = f"{test_owner.Team.MULTIPOD.value}/maxtext"

    test_group_id = "chained_tests" + "_" + model + "_" + "stable"

    with TaskGroup(group_id=test_group_id, prefix_group_id=False) as group:
      shared_gcs_location = name_format.generate_gcs_folder_location.override(
          task_id=f"{test_group_id}_generate_gcs_folder_location"
      )(
          gcs_subfolder,
          test_group_id,
      )
      stable_cpu = gke_config.get_maxtext_cpu_end_to_end_gke_config(
          time_out_in_min=test_scripts_details[0]["time_out_in_min"],
          test_name=f"{test_name_prefix}-stable-{model}",
          run_model_cmds=(
              f"export BASE_OUTPUT_PATH=$GCS_OUTPUT; bash end_to_end/{test_scripts_details[0]['script_name']}.sh",
          ),
          cluster=test_scripts_details[0]["cluster"],
          docker_image=DockerImage.MAXTEXT_TPU_JAX_STABLE_STACK.value,
          test_owner=test_owner.ANISHA_M,
      ).run(gcs_location=shared_gcs_location)
      stable_tpu = gke_config.get_gke_config(
          time_out_in_min=test_scripts_details[1]["time_out_in_min"],
          test_name=f"{test_name_prefix}-stable-{model}",
          run_model_cmds=(
              f"export BASE_OUTPUT_PATH=$GCS_OUTPUT; bash end_to_end/{test_scripts_details[1]['script_name']}.sh",
          ),
          docker_image=DockerImage.MAXTEXT_TPU_JAX_STABLE_STACK.value,
          test_owner=test_owner.ANISHA_M,
          cluster=test_scripts_details[1]["cluster"],
      ).run(gcs_location=shared_gcs_location)

    test_group_id = "chained_tests" + "_" + model + "_" + "nightly"

    with TaskGroup(group_id=test_group_id, prefix_group_id=False) as group:
      shared_gcs_location = name_format.generate_gcs_folder_location.override(
          task_id=f"{test_group_id}_generate_gcs_folder_location"
      )(
          gcs_subfolder,
          test_group_id,
      )
      nightly_cpu = gke_config.get_maxtext_cpu_end_to_end_gke_config(
          time_out_in_min=test_scripts_details[0]["time_out_in_min"],
          test_name=f"{test_name_prefix}-nightly-{model}",
          run_model_cmds=(
              f"export BASE_OUTPUT_PATH=$GCS_OUTPUT; bash end_to_end/{test_scripts_details[0]['script_name']}.sh",
          ),
          cluster=test_scripts_details[0]["cluster"],
          docker_image=DockerImage.MAXTEXT_TPU_JAX_NIGHTLY.value,
          test_owner=test_owner.ANISHA_M,
      ).run(gcs_location=shared_gcs_location)
      nightly_tpu = gke_config.get_gke_config(
          time_out_in_min=test_scripts_details[1]["time_out_in_min"],
          test_name=f"{test_name_prefix}-nightly-{model}",
          run_model_cmds=(
              f"export BASE_OUTPUT_PATH=$GCS_OUTPUT; bash end_to_end/{test_scripts_details[1]['script_name']}.sh",
          ),
          docker_image=DockerImage.MAXTEXT_TPU_JAX_NIGHTLY.value,
          test_owner=test_owner.ANISHA_M,
          cluster=test_scripts_details[1]["cluster"],
      ).run(gcs_location=shared_gcs_location)
      stable_cpu >> stable_tpu >> nightly_cpu >> nightly_tpu
