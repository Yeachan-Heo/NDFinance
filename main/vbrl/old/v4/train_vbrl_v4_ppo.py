from blqt.rl_envs.vb_env import VBEnv_V4

from ray import tune
from ray.rllib.agents import ppo
import numpy as np

if __name__ == '__main__':
    config = ppo.DEFAULT_CONFIG.copy()
    config["env"] = VBEnv_V4

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
        local_dir="/home/bellmanlabs/Projects/ray_results/VBEnv_V4_0.1",
    )
