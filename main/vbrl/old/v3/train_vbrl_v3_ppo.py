from blqt.rl_envs.vb_env import VBEnv_V3

from ray import tune
from ray.rllib.agents import ppo
import numpy as np

if __name__ == '__main__':
    config = ppo.DEFAULT_CONFIG.copy()
    config["env"] = VBEnv_V3

    config["env_config"] = {
        "data_path_1min" : "/home/bellmanlabs/Data/bitmex/trade/ohlc/XBTUSD_1H.csv",
        "data_path_1day": "/home/bellmanlabs/Data/bitmex/trade/ohlc/XBTUSD_1D.csv",
        "from_timeindex" : -np.inf,
        "to_timeindex" : "2018-10-01",
        "k" : 0.6
    }

    config["framework"] = "tf"
    config["num_workers"] = 11
    config["num_gpus"] = 1

    tune.run(
        ppo.PPOTrainer,
        config=config,
        checkpoint_freq=50,
        checkpoint_at_end=True,
        local_dir="/home/bellmanlabs/Projects/ray_results/VBEnv_V3",
        restore="/home/bellmanlabs/Projects/ray_results/VBEnv_V3/PPO/PPO_VBEnv_V3_0_2020-09-08_09-29-03_hgfo9pp/checkpoint_4700/checkpoint-4700"
    )
