from blqt.rl_envs.vb_env import VBEnv_V3
from ray import tune
from ray.rllib.agents import ppo

if __name__ == '__main__':
    config = ppo.DEFAULT_CONFIG.copy()
    config["env"] = VBEnv_V3

    config["env_config"] = {
        "data_path_1min" : "/tmp/pycharm_project_716/data/bitmex/XBTUSD_1H.csv",
        "data_path_1day": "/tmp/pycharm_project_716/data/bitmex/XBTUSD_1D.csv",
        "from_timeindex" : -np.inf,
        "to_timeindex" : np.inf,
        "k" : 0.6
    }

    config["framework"] = "torch"
    config["num_workers"] = 11
    config["num_gpus"] = 1

    tune.run(
        ppo.PPOTrainer,
        config=config,
        checkpoint_freq=100,
        checkpoint_at_end=True,
        local_dir="./log",
    )
