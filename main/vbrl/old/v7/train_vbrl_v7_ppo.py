from blqt.rl_envs.vb_env import VBEnv_V7

from ray import tune
from ray.rllib.agents import ppo
import numpy as np

if __name__ == '__main__':
    config = ppo.DEFAULT_CONFIG.copy()
    config["env"] = VBEnv_V7

    config["env_config"] = {
        "data_path_1min" : "/home/bellmanlabs/Data/bitmex/trade/ohlc/1H/XBTUSD.csv",
        "data_path_1day": "/home/bellmanlabs/Data/bitmex/trade/ohlc/1D/XBTUSD.csv",
        "from_timeindex" : -np.inf,
        "to_timeindex" : np.inf,
        "k" : 0.6
    }

    config["framework"] = "tf"
    config["num_workers"] = 11
    config["num_gpus"] = 1
    config["seed"] = 7777

    tune.run(
        ppo.PPOTrainer,
        config=config,
        checkpoint_freq=50,
        checkpoint_at_end=True,
        local_dir="/home/bellmanlabs/Projects/ray_results/VBEnv_V7/",
        #restore="/home/bellmanlabs/Projects/ray_results/VBEnv_V5/PPO/PPO_VBEnv_V5_0_2020-09-08_19-19-255acmfhzc/checkpoint_6250/checkpoint-6250"
    )
