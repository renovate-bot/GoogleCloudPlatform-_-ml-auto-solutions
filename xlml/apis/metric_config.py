# Copyright 2023 Google LLC
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

"""Config file for benchmark metrics."""

import dataclasses
import enum
from typing import Iterable, List, Optional


# TODO(ranran): add project info to let users specify dataset location
class DatasetOption(enum.Enum):
  BENCHMARK_DATASET = "benchmark_dataset"
  XLML_DATASET = "xlml_dataset"


class FormatType(enum.Enum):
  JSON_LINES = enum.auto()
  TENSORBOARD_SUMMARY = enum.auto()
  PROFILE = enum.auto()


class AggregationStrategy(enum.Enum):
  LAST = enum.auto()
  AVERAGE = enum.auto()
  MEDIAN = enum.auto()


class SshEnvVars(enum.Enum):
  GCS_OUTPUT = "${GCS_OUTPUT}"
  BASE_OUTPUT_PATH = "${BASE_OUTPUT_PATH}"


@dataclasses.dataclass
class JSONLinesConfig:
  """A class to set up JSON Lines config.

  Attributes:
    file_location: The location of the file in GCS. When
      `use_runtime_generated_gcs_folder` flag is true, use relative path.
  """

  file_location: str


@dataclasses.dataclass
class SummaryConfig:
  """A class to set up TensorBoard summary config.

  Attributes:
    file_location: The location of the file in GCS. When
      `use_runtime_generated_gcs_folder` flag is true, use relative path.
    aggregation_strategy: The aggregation strategy for metrics.
    include_tag_patterns: The matching patterns of tags that wil be included.
      All tags are included by default.
    exclude_tag_patterns: The matching patterns of tags that will be excluded.
      No tag is excluded by default. This pattern has higher prioirty to
      include_tag_pattern.
    use_regex_file_location: Whether to use file_location as a regex to get the
      file in GCS.
  """

  file_location: str
  aggregation_strategy: AggregationStrategy
  include_tag_patterns: Optional[Iterable[str]] = None
  exclude_tag_patterns: Optional[Iterable[str]] = None
  use_regex_file_location: bool = False


@dataclasses.dataclass
class ProfileConfig:
  """A class to set up profile config.

  Attributes:
    file_location: directory holding profile.
      Profile is located in `{file_location}/.*/*xplane.pb`
    metrics: placeholder, to be populated by `metric.xplane_to_metrics`
  """

  file_location: str
  metrics: Optional[dict] = None


@dataclasses.dataclass
class MetricConfig:
  """A class to set up config of Benchmark metric, dimension, and profile.

  Attributes:
    json_lines: The config for JSON Lines input.
    tensorboard_summary: The config for TensorBoard summary input.
    profile: The config for profile input.
    use_runtime_generated_gcs_folder: Indicator to use path based on
      benchmark_id from generate_gcs_folder_location()
  """

  json_lines: Optional[JSONLinesConfig] = None
  tensorboard_summary: Optional[SummaryConfig] = None
  profile: Optional[ProfileConfig] = None
  use_runtime_generated_gcs_folder: bool = False
