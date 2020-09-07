from blqt.rl_envs.timecut_env import TimeCutEnv
from ray.rllib.agents import sac
import ray.tune as tune

if __name__ == '__main__':
    config = sac.DEFAULT_CONFIG.copy()
    config["env"] = TimeCutEnv

    config["env_config"] = {
        "data_path" : "/tmp/pycharm_project_22/data/bitmex/XBTUSD_1H.csv"
    }

    config["framework"] = "torch"
    config["num_workers"] = 11
    config["num_gpus"] = 1

    tune.run(
        sac.SACTrainer,
        config=config,
        checkpoint_freq=100,
        checkpoint_at_end=True,
        local_dir="./log",
    )
