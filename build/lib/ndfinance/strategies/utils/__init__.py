import numpy as np

def apply_n_percent_rule(value, n_percent=5, loss_cut_percent=20):
    return (value * n_percent / 100) / (loss_cut_percent / 100)