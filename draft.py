from ray.rllib.models.tf import TFModelV2
from tensorflow.keras import *


def add_cnn_layers(x, label):
    x = layers.Conv2D(filters=32, kernel_size=(5, 5), strides=(1, 1), activation="relu",
                      name=f"{label}_cnn_1")(x)
    x = layers.MaxPool2D((2, 2), name=f"{label}_pool_1")(x)
    x = layers.Conv2D(filters=32, kernel_size=(5, 5), strides=(1, 1), activation="relu",
                      name=f"{label}_cnn_2")(x)
    x = layers.MaxPool2D((2, 2), name=f"{label}_pool_2")(x)
    x = layers.Conv2D(filters=32, kernel_size=(5, 5), strides=(1, 1), activation="relu",
                      name=f"{label}_cnn_3")(x)
    x = layers.MaxPool2D((2, 2), name=f"{label}_pool_3")(x)
    x = layers.Flatten()(x)
    x = layers.Dense(256, x, activation="relu", name=f"{label}_dense_1")(x)
    return x


def add_dense_layers(x, label):
    x = layers.Dense(256, x, activation="relu", name=f"{label}_dense_1")(x)
    x = layers.Dense(256, x, activation="relu", name=f"{label}_dense_2")(x)
    return x

class SboxCustomModel(TFModelV2):
    def __init__(self, *args, **kwargs):
        super(SboxCustomModel, self).__init__(*args, **kwargs)
        output_size = self.model_config["output_size"]

        input_lat = layers.Input(shape=(256, 256))
        input_ddt = layers.Input(shape=(256, 256))
        input_sbox = layers.Input(shape=(256,))

        output_lat = add_cnn_layers(input_lat, "LAT")
        output_ddt = add_cnn_layers(input_ddt, "DDT")
        output_sbox = add_dense_layers(input_sbox, "Sbox")

        concat = layers.Concatenate(name="concat_1")(output_ddt, output_lat, output_sbox)

        x = layers.Dense(1024, activation="relu", name="dense_1")(concat)
        x = layers.Dense(1024, activation="relu", name="dense_2")(x)
        policy = layers.Dense(output_size, name="output_policy")(x)
        value = layers.Dense(1, name="output_value")(x)

        self.base_model = models.Model(inputs=(input_lat, input_ddt, input_sbox),
                                       outputs=(policy, value))

        self.register_variables(self.base_model.variables)


    def forward(self, input_dict, state, seq_lens):
        out, self._value_out = self.base_model(input_dict["obs"])
        return out

    def value_function(self):
        return self._value_out


