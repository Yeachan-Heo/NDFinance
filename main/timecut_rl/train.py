from blqt.rl_envs.timecut_env import TimeCutCryptoEnv
from ray.rllib.agents import ppo
import ray.tune as tune

if __name__ == '__main__':
    config = ppo.DEFAULT_CONFIG.copy()
    config["env"] = TimeCutCryptoEnv

    config["env_config"] = {
        "data_path" : "/tmp/pycharm_project_716/data/bitmex/XBTUSD_1H.csv"
    }

    config["framework"] = "torch"
    config["num_workers"] = 11

    tune.run(
        ppo.PPOTrainer,
        config=config,
        checkpoint_freq=100,
        checkpoint_at_end=True,
        local_dir="./TimeCut_Env/",
    )
