# Experiment

English | [中文](README.zh-CN.md)

This directory organizes experiment data and scripts by data lifecycle:

- `inputs/raw/`: raw plugin outputs or raw experiment results
- `inputs/aligned/`: intermediate results aligned to the 945 valid samples
- `outputs/plugin_comparison/`: scoring tables and exported results for plugin comparison
- `outputs/recommendation/`: generated outputs for model recommendation experiments
- `outputs/system_test_reports/`: system test reports
- `scripts/`: experiment and test scripts
- `configs/`: script configuration templates and scoring configuration

## Workflow

1. Prepare recommendation generation configuration based on `configs/recommendation_experiment_config.example.json`, then run `scripts/run_recommendation_generation_experiment.py` to generate multi-model candidate outputs.
2. Run `scripts/run_model_recommendation_experiment.py` to replay the model recommendation strategy.
3. Use `configs/score_config.json` and `scripts/score_merged.py` to compute plugin comparison metrics.
4. Run `scripts/summarize_scored_results.py` to summarize plugin comparison results.
5. Prepare system test configuration based on `configs/system_test_config.example.json`, then run `scripts/run_system_test_suite.py` to generate system test reports.
