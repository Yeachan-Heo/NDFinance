from blqt.rl_envs.vb_env import *


if __name__ == '__main__':
    config = ppo.DEFAULT_CONFIG.copy()
    config["env"] = VBEnv

    config["env_config"] = {
        "data_path_1min" : "/tmp/pycharm_project_716/data/bitmex/XBTUSD_1H.csv",
        "data_path_1day": "/tmp/pycharm_project_716/data/bitmex/XBTUSD_1D.csv",
        "from_timeindex" : -np.inf,
        "to_timeindex" : np.inf
    }

    config["framework"] = "torch"
    config["num_workers"] = 11

    tune.run(
        ppo.PPOTrainer,
        config=config,
        checkpoint_freq=100,
        checkpoint_at_end=True,
        local_dir="./VB_Env/",
    )
