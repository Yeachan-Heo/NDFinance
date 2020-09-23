class Logger:
    def __init__(self):
        super(Logger, self).__init__()
        self.value = {}

    def add_label(self, label):
        self.value[label] = []

    def add_scalar(self, label, scalar):
        self.value[label].append(scalar)

    def set_engine(self, engine):
        self.engine = engine
        self.broker = self.engine.broker
        self.data_provider = self.engine.data_provider