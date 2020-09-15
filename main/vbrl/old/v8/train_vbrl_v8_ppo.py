from blqt.rl_envs.vb_env import VBEnv_V8

from ray import tune
from ray.rllib.agents import ppo
import numpy as np

if __name__ == '__main__':
    config = ppo.DEFAULT_CONFIG.copy()
    config["env"] = VBEnv_V8

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
        local_dir="/home/bellmanlabs/Data/Projects/ray_results/VBEnv_V8/",
        restore="/home/bellmanlabs/Data/Projects/ray_results/VBEnv_V8/PPO/PPO_VBEnv_V8_0_2020-09-12_00-32-22tgc4l_mu/checkpoint_3900/checkpoint-3900",
    )
