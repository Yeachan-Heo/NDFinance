import gym
from ndfinance.brokers.backtest import *


DEFAULT_ENV_CONFIG = {
    "broker" : None,
    "episode_len" : TimeFrames.day * 30,
    "step_len" : TimeFrames.hour,

}

class SingleTickerTradingEnvironmentBase(gym.Env):
    def __init__(self, env_config):
        super(SingleTickerTradingEnvironmentBase, self).__init__()
        self.broker: BacktestBroker = env_config["broker"]   
        self.episode_len = env_config["episode_len"]
        self.step_len = env_config["step_len"]
        self.data_provider: BacktestDataProvider = self.broker.data_proovider
        self.indexer: TimeIndexer = self.broker.indexer
        self.step_ckpt = self.episode_ckpt = self.broker.indexer.timestamp

    def logic(self, *args, **kwargs):
        raise NotImplementedError

    def get_reward(self):
        raise NotImplementedError

    def get_reward_end(self):
        return self.get_reward()

    def get_observation(self):
        raise NotImplementedError

    def _is_done(self, now, ckpt, leng):
        if now - ckpt >= leng:
            return True, now
        return False, ckpt

    def is_step_done(self):
        ret, self.step_ckpt = self._is_done(
            self.indexer.timestamp, self.step_ckpt, self.step_len)
        return ret

    def is_episode_done(self):
        ret, self.episode_ckpt = self._is_done(
            self.indexer.timestamp, self.episode_ckpt, self.step_len)
        return ret

    def reset_engine(self):
        self.indexer.reset()
        self.broker.reset()

    def indexer_is_done(self):
        ret = self.indexer.is_done()
        if ret: self.indexer.reset()
        return ret

    def step(self):
        while not self.is_step_done():
            self.logic()
            self.indexer.move()
            if self.is_episode_done() or self.indexer_is_done():
                return self.get_observation(), self.get_reward_end(), True
        
        return self.get_observation(), self.get_reward(), self.is_episode_done()

    
    

        
    

    