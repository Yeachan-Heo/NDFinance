import ray
import numpy as np
from ray import tune
from ray.rllib.agents import ppo
from blqt.rl_envs.vb_env import VBRLEnv
from blqt.backtest.base import TimeFrames

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
    ray.init()

    tune.run(
        ppo.PPOTrainer,
        config=config,
        checkpoint_freq=50,
        checkpoint_at_end=True,
        local_dir=f"/home/bellmanlabs/Data/Projects/ray_results/VBRL/{k}_{time_cut}_{default_reward}_{min_bet}_{max_leverage}/",
        stop={"episodes_total": 10000}
    )

if __name__ == '__main__':
    last_cfg = 0
    cfgs = []
    episode_len = TimeFrames.Day * 200
    
    for k in [0.5, 0.6, 0.7]:
        for time_cut in [3, 9, 15]:
            for default_reward in [-0.01, -0.03, -0.05]:
                for min_bet in [0, 0.2, 0.4]:
                    for max_leverage in [1, 2, 3]:
                        cfgs.append((k, time_cut, episode_len, default_reward, min_bet, max_leverage)) 
    
    for i, cfg in enumerate(cfgs[last_cfg:]):
        print(f"running config i:{cfg}")
        main(*cfg)