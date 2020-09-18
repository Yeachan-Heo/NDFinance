import ray
import numpy as np
from ray import tune
from ray.rllib.agents import ppo
from blqt.rl_envs.vb_env import VBRLEnv
from blqt.backtest.base import TimeFrames
import multiprocessing

def main(k, time_cut, episode_len, default_reward, min_bet, max_leverage):

    config = ppo.DEFAULT_CONFIG.copy()
    config["env"] = VBRLEnv

    config["env_config"] = {

        "data_path_1min" : [
            "/home/bellmanlabs/Data/bitmex/trade/ohlc/1H/XBTUSD.csv",
            "/home/bellmanlabs/Data/bitmex/trade/ohlc/1H/ETHUSD.csv",
                                           ],

        "data_path_1day": [
                "/home/bellmanlabs/Data/bitmex/trade/ohlc/1D/XBTUSD.csv",
                "/home/bellmanlabs/Data/bitmex/trade/ohlc/1D/ETHUSD.csv",
                                           ],

        "default_reward" : default_reward,
        "max_leverage": max_leverage,
        "from_timeindex" : -np.inf,
        "to_timeindex" : np.inf,
        "episode_len": episode_len,
        "time_cut" : time_cut,
        "min_bet": min_bet,
        "k" : k,

    }

    config["framework"] = "tf"
    config["num_workers"] = 11
    config["num_gpus"] = 1
    
    ray.shutdown()
    ray.init(memory=1024*1024*8000)

    tune.run(
        ppo.PPOTrainer,
        config=config,
        checkpoint_freq=50,
        checkpoint_at_end=True,
        local_dir=f"/home/bellmanlabs/Data/Projects/ray_results/VBRL/{k}_{time_cut}_{default_reward}_{min_bet}_{max_leverage}/",
        stop={"training_iteration": 500}
    )

def main_async(cfg):
    print(f"running config {cfgs.index(cfg)}:{cfg}")
    return main(*cfg)

import os

if __name__ == '__main__':
    cfgs = []
    episode_len = TimeFrames.Day * 200
    for k in [0.5, 0.6, 0.7]:
        for time_cut in [3, 9, 15]:
            for default_reward in [-0.03, -0.05, -0.1]:
                for min_bet in [0, 0.2]:
                    for max_leverage in [1, 3]:
                        cfgs.append((k, time_cut, episode_len, default_reward, min_bet, max_leverage))

    for i, cfg in enumerate(cfgs):
        k, time_cut, episode_len, default_reward, min_bet, max_leverage = cfg
        if not os.path.exists(f"/home/bellmanlabs/Data/Projects/ray_results/VBRL/{k}_{time_cut}_{default_reward}_{min_bet}_{max_leverage}/"):
            main_async(cfg)
        else:
            print(f"experiment no: {i} already exists, aborting")