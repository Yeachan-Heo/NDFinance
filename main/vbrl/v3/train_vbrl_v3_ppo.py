from blqt.rl_envs.vb_env import VBEnv_V3

from ray import tune
from ray.rllib.agents import ppo
import numpy as np

if __name__ == '__main__':
    config = ppo.DEFAULT_CONFIG.copy()
    config["env"] = VBEnv_V3

    config["env_config"] = {
        "data_path_1min" : "/tmp/pycharm_project_22/data/bitmex/XBTUSD_1H.csv",
        "data_path_1day": "/tmp/pycharm_project_22/data/bitmex/XBTUSD_1D.csv",
        "from_timeindex" : -np.inf,
        "to_timeindex" : "2018-10-01",
        "k" : 0.6
    }

    config["framework"] = "torch"
    config["num_workers"] = 11
    config["num_gpus"] = 1
    config["seed"] = 7777777

    tune.run(
        ppo.PPOTrainer,
        config=config,
        checkpoint_freq=100,
        checkpoint_at_end=True,
        local_dir="./log/xbt_partial",
        #restore="/tmp/pycharm_project_22/main/vbrl/v3/log/xbt_partial/PPO/PPO_VBEnv_V3_0_2020-09-07_10-12-37qv3rf7b8/checkpoint_700/checkpoint-700"
    )
