import argparse
import os
import shutil
from datetime import datetime
from typing import Union
from pathlib import Path
import haiku as hk
import jax
import jax.numpy as jnp
import numpy as np
import optax
import wandb
from agent_core import AgentCore

os.environ["KMP_DUPLICATE_LIB_OK"] = "True"
from class_Graph_generation import sample_padded_grid_batch_shortest_path
from class_grid_run_config import GridConfig
from class_models import get_forward_function
from class_plotting_utils import (
    plot_graph_grid_activations,
    plot_input_target_output,
    plot_message_passing_layers,
    plot_xy,
)
from class_utils import rng_sequence_from_rng, set_device
from sklearn.metrics import matthews_corrcoef, roc_auc_score

# @title Graph net functions
parser = argparse.ArgumentParser()
parser.add_argument(
    "--config_path",
    metavar="-C",
    default="class_config.yaml",
    help="path to base configuration file.",
)

class Domine2023(AgentCore):

    def __init__ (
        self,
        agent_name: str = "SR",
        experiment_name = 'smaller size generalisation graph with  no position feature',
        train_on_shortest_path: bool = True,
        resample: bool = True,
        wandb_on: bool = False,
        seed: int = 41,
        feature_position: bool = False,
        weighted: bool = True,
        num_hidden: int = 100,
        num_layers : int = 2,
        num_message_passing_steps: int = 3,
        learning_rate: float = 0.001,
        num_training_steps: int = 10,
        batch_size: int = 4,
        nx_min:  int = 4,
        nx_max: int = 7,
        batch_size_test: int= 4,
        nx_min_test: int = 4 ,
        nx_max_test: int = 7,
        **mod_kwargs,
    ):
        self.train_on_shortest_path = train_on_shortest_path
        self.experiment_name = experiment_name  # config.experiment_name
        self.train_on_shortest_path = train_on_shortest_path  # cconfig.train_on_shortest_path
        self.resample = resample  # config.resample  # @param
        self.wandb_on = wandb_on  # cconfig.wandb_on
        self.seed = seed  # cconfig.seed

        self.feature_position = feature_position # cconfig.feature_position
        self.weighted = weighted  # cconfig.weighted

        self.num_hidden = num_hidden  # cconfig.num_hidden  # @param
        self.num_layers = num_layers   # cconfig.num_layers  # @param
        self.num_message_passing_steps = num_message_passing_steps  # cconfig.num_training_steps  # @param
        self.learning_rate = learning_rate  # cconfig.learning_rate  # @param
        self.num_training_steps = num_training_steps # cconfig.num_training_steps  # @param

        self.batch_size =batch_size  # cconfig.batch_size
        self.nx_min = nx_min  # cconfig.nx_min
        self.nx_max = nx_max  # cconfig.nx_max
        self.arena_x_limits = mod_kwargs["arena_y_limits"]  # cmod_kwargs["arena_x_limits"]
        self.arena_y_limits = mod_kwargs["arena_y_limits"]
        self.room_width = np.diff(self.arena_x_limits)[0]
        self.room_depth = np.diff(self.arena_y_limits)[0]

        # This can be tought of the brain making different rep of different  granularity
        # Could be explained during sleep
        self.batch_size_test = batch_size_test  # cconfig.batch_size_test
        self.nx_min_test = nx_min_test  # cconfig.nx_min_test  # This is thought of the state density
        self.nx_max_test = nx_max_test # config.nx_max_test  # This is thought of the state density
        self.batch_size = batch_size  # c config.batch_size
        self.nx_min = nx_min  # c config.nx_min  # This is thought of the state density
        self.nx_max = nx_max  # c config.nx_max  # This is thought of the state density

        # TODO: Make sure that for different graph this changes with the environement
        # self.ny_min_test = config.ny_min_test  # This is thought of the state density
        # self.ny_max_test = config.ny_max_test  # This is thought of the state density
        # self.ny_min = con
        # fig.ny_min  # This is thought of the state density
        # self.ny_max = config.ny_max  # This is thought of the state density

        # self.resolution_x_min_test = int(self.nx_min * self.room_width)
        # self.resolution_x_max_test = int(self.nx_max * self.room_depth)
        # self.resolution_x_min = int(self.nx_min_test * self.room_width)
        # self.resolution_x_max = int(self.nx_max_test * self.room_depth)

        # self.resolution_y_min_test = int(self.nx_min * self.room_width)
        # self.resolution_y_max_test = int(self.nx_max * self.room_depth)
        # self.resolution_y_min = int(self.nx_min_test * self.room_width)
        # self.resolution_y_max = int(self.nx_max_test * self.room_depth)

        self.log_every = config.num_training_steps // 10
        if self.weighted:
            self.edege_lables = True
        else:
            self.edege_lables = False
        if self.wandb_on:
            dateTimeObj = datetime.now()
            wandb.init(
                project="graph-brain", entity="graph-brain",
                name="Grid_shortest_path" + dateTimeObj.strftime("%d%b_%H_%M")
            )
            self.wandb_logs = {}
            save_path = wandb.run.dir
            os.mkdir(os.path.join(save_path, "results"))
            self.save_path = os.path.join(save_path, "results")

        else:
            dateTimeObj = datetime.now()
            save_path = os.path.join(Path(os.getcwd()).resolve(), "results")
            os.mkdir(os.path.join(save_path, "Grid_shortest_path" + dateTimeObj.strftime("%d%b_%H_%M")))
            self.save_path = os.path.join(
                os.path.join(save_path, "Grid_shortest_path" + dateTimeObj.strftime("%d%b_%H_%M")))

        # SAVING Trainning Files
        path = os.path.join(self.save_path, "run.py")
        HERE = os.path.join(Path(os.getcwd()).resolve(), "domine_2023.py")
        shutil.copyfile(HERE, path)

        path = os.path.join(self.save_path, "class_Graph_generation.py")
        HERE = os.path.join(Path(os.getcwd()).resolve(), "class_Graph_generation.py")
        shutil.copyfile(HERE, path)

        path = os.path.join(self.save_path, "class_utils.py")
        HERE = os.path.join(Path(os.getcwd()).resolve(), "class_utils.py")
        shutil.copyfile(HERE, path)

        path = os.path.join(self.save_path, "class_plotting_utils.py")
        HERE = os.path.join(Path(os.getcwd()).resolve(), "class_plotting_utils.py")
        shutil.copyfile(HERE, path)

        path = os.path.join(self.save_path, "class_config_run.yaml")
        HERE = os.path.join(Path(os.getcwd()).resolve(), "class_config.yaml")
        shutil.copyfile(HERE, path)

        # This is the function that does the forward pass of the model
        self.reset()

    def evaluate(self, model, params, inputs, target):
        outputs = model.apply(params, inputs)
        roc_auc = roc_auc_score(np.squeeze(target), np.squeeze(outputs[0].nodes))
        MCC = matthews_corrcoef(np.squeeze(target), round(np.squeeze(outputs[0].nodes)))

        return outputs, roc_auc, MCC


    def reset(self,a=1):

        self.global_steps = 0
        self.losses = []
        self.losses_test = []
        self.roc_aucs_train = []
        self.MCCs_train = []
        self.MCCs_test = []
        self.roc_aucs_test = []


        return


    def update(self):
        forward = get_forward_function(self.num_hidden, self.num_layers, self.num_message_passing_steps)
        net_hk = hk.without_apply_rng(hk.transform(forward))
        self.rng = jax.random.PRNGKey(self.seed)
        self.rng_seq = rng_sequence_from_rng(self.rng)

        if self.train_on_shortest_path:
            graph, targets = sample_padded_grid_batch_shortest_path(
                self.rng, self.batch_size, self.feature_position, self.weighted, self.nx_min, self.nx_max
            )
        else:
            graph, targets = sample_padded_grid_batch_shortest_path(
                self.rng, self.batch_size, self.feature_position, self.weighted, self.nx_min, self.nx_max
            )
        self.params = net_hk.init(self.rng, graph)
        optimizer = optax.adam(self.learning_rate)
        self.opt_state = optimizer.init(self.params)

        @jax.jit
        def compute_loss(params, inputs, targets):
            # not jitted because it will get jitted in jax.value_and_grad
            outputs = net_hk.apply(params, inputs)
            return jnp.mean((outputs[0].nodes - targets) ** 2)  # using MSE

        @jax.jit
        def update_step(grads, opt_state, params, ):
            updates, opt_state = optimizer.update(grads, opt_state, params)
            params = optax.apply_updates(params, updates)
            return params

        rng = next(self.rng_seq)
        graph_test, target_test = sample_padded_grid_batch_shortest_path(
            rng, self.batch_size_test, self.feature_position, self.weighted, self.nx_min_test, self.nx_max_test
        )
        rng = next(self.rng_seq)
        # Sample a new batch of graph every itterations
        if self.resample:
            if self.train_on_shortest_path:
                graph, targets = sample_padded_grid_batch_shortest_path(
                    rng, self.batch_size, self.feature_position, self.weighted, self.nx_min, self.nx_max
                )
            else:
                graph, targets = sample_padded_grid_batch_shortest_path(
                    rng, self.batch_size, self.feature_position, self.weighted, self.nx_min, self.nx_max
                )
                targets = graph.nodes
        # Train
        loss, grads = jax.value_and_grad(compute_loss)(
            self.params, graph, targets
        )  # jits inside of value_and_grad
        self.params = update_step(grads, self.opt_state, self.params)
        self.losses.append(loss)
        outputs_train, roc_auc_train, MCC_train = self.evaluate(net_hk, self.params, graph, targets)
        self.roc_aucs_train.append(roc_auc_train)
        self.MCCs_train.append(MCC_train)  # Matthews correlation coefficient
        # Test # model should basically learn to do nothing from this
        loss_test = compute_loss(self.params,graph_test, target_test)
        self.losses_test.append(loss_test)
        outputs_test, roc_auc_test, MCC_test = self.evaluate(net_hk, self.params, graph_test, target_test)
        self.roc_aucs_test.append(roc_auc_test)
        self.MCCs_test.append(MCC_test)
        self.net_hk = net_hk

        # Log
        wandb_logs = {"loss": loss, "losses_test": loss_test, "roc_auc_test": roc_auc_test, "roc_auc": roc_auc_train}
        if self.wandb_on:
            wandb.log(wandb_logs)
        self.global_steps = self.global_steps + 1
        if self.global_steps % self.log_every == 0:
            print(f"Training step {n}: loss = {loss}")
        return

    def act(self):
        pass

    def print_and_plot(self):
        # EVALUATE
        rng = next(self.rng_seq)
        graph_test, target_test = sample_padded_grid_batch_shortest_path(
            rng, self.batch_size_test, self.feature_position, self.weighted, self.nx_min_test, self.nx_max_test
        )
        outputs, roc_auc, MCC = self.evaluate(self.net_hk, self.params, graph_test, target_test)
        print("roc_auc_score")
        print(roc_auc)
        print("MCC")
        print(MCC)

        # SAVE PARAMETER (NOT WE SAVE THE FILES SO IT SHOULD BE THERE AS WELL )
        if self.wandb_on:
            with open("readme.txt", "w") as f:
                f.write("readme")
            with open(os.path.join(self.save_path, "Constant.txt"), "w") as outfile:
                outfile.write("num_message_passing_steps" + str(self.num_message_passing_steps) + "\n")
                outfile.write("Learning_rate:" + str(self.learning_rate) + "\n")
                outfile.write("num_training_steps:" + str(self.num_training_steps))
                outfile.write("roc_auc" + str(roc_auc))
                outfile.write("MCC" + str(MCC))

        # PLOTTING THE LOSS and AUC ROC
        plot_xy(self.losses, os.path.join(self.save_path, "Losses.pdf"), "Losses")
        plot_xy(self.losses_test, os.path.join(self.save_path, "Losses_test.pdf"), "Losses_test")
        plot_xy(self.roc_aucs_test, os.path.join(self.save_path, "auc_roc_test.pdf"), "auc_roc_test")
        plot_xy(self.roc_aucs_train, os.path.join(self.save_path, "auc_roc_train.pdf"), "auc_roc_train")
        plot_xy(self.MCCs_train, os.path.join(self.save_path, "MCC_train.pdf"), "MCC_train")
        plot_xy(self.MCCs_test, os.path.join(self.save_path, "MCC_test.pdf"), "MCC_test")

        # PLOTTING ACTIVATION OF THE FIRST 2 GRAPH OF THE BATCH
        plot_input_target_output(
            list(graph_test.nodes.sum(-1)),
            target_test.sum(-1),
            outputs[0].nodes.tolist(),
            graph_test,
            4,
            self.edege_lables,
            os.path.join(self.save_path, "in_out_targ.pdf"),
        )
        plot_message_passing_layers(
            list(graph_test.nodes.sum(-1)),
            outputs[1],
            target_test.sum(-1),
            outputs[0].nodes.tolist(),
            graph_test,
            3,
            self.num_message_passing_steps,
            self.edege_lables,
            os.path.join(self.save_path, "message_passing_graph.pdf"),
        )
        # plot_message_passing_layers_units(outputs[1], target_test.sum(-1), outputs[0].nodes.tolist(),graph_test,config.num_hidden,config.num_message_passing_steps,edege_lables,os.path.join(save_path, 'message_passing_hidden_unit.pdf'))

        # Plot each seperatly
        plot_graph_grid_activations(
            outputs[0].nodes.tolist(),
            graph_test,
            os.path.join(self.save_path, "outputs.pdf"),
            "Predicted Node Assignments with GCN",
            self.edege_lables,
        )
        plot_graph_grid_activations(
            list(graph_test.nodes.sum(-1)),
            graph_test,
            os.path.join(self.save_path, "Inputs.pdf"),
            "Inputs node assigments",
            self.edege_lables,
        )
        plot_graph_grid_activations(
            target_test.sum(-1), graph_test, os.path.join(self.save_path, "Target.pdf"), "Target", self.edege_lables
        )

        plot_graph_grid_activations(
            outputs[0].nodes.tolist(),
            graph_test,
            os.path.join(self.save_path, "outputs_2.pdf"),
            "Predicted Node Assignments with GCN",
            self.edege_lables,
            2,
        )
        plot_graph_grid_activations(
            list(graph_test.nodes.sum(-1)),
            graph_test,
            os.path.join(self.save_path, "Inputs_2.pdf"),
            "Inputs node assigments",
            self.edege_lables,
            2,
        )
        plot_graph_grid_activations(
            target_test.sum(-1), graph_test, os.path.join(self.save_path, "Target_2.pdf"), "Target", self.edege_lables, 2
        )
        return


if __name__ == "__main__":
    from neuralplayground.arenas import Simple2D

    args = parser.parse_args()
    set_device()
    config_class = GridConfig
    config = config_class(args.config_path)
    time_step_size = 0.1  # seg
    agent_step_size = 3

    # Init environment
    arena_x_limits = [-100, 100]
    arena_y_limits = [-100, 100]
    env = Simple2D(
        time_step_size=time_step_size,
        agent_step_size=agent_step_size,
        arena_x_limits=arena_x_limits,
        arena_y_limits=arena_y_limits,
    )

    experiment_name= 'smaller size generalisation graph with  no position feature'
    train_on_shortest_path= True
    resample= True  # @param
    wandb_on= True
    seed= 41

    feature_position= False
    weighted= True

    num_hidden= 100  # @param
    num_layers= 2  # @param
    num_message_passing_steps= 3  # @param
    learning_rate= 0.001  # @param
    num_training_steps= 10  # @param

    # Env Stuff
    batch_size= 4
    nx_min= 4
    nx_max= 7

    batch_size_test= 4
    nx_min_test= 4
    nx_max_test= 7

    agent = Domine2023(
        arena_y_limits=arena_y_limits, arena_x_limits=arena_x_limits
    )
    for n in range(config.num_training_steps):
        agent.update()

    agent.print_and_plot()


# TODO: Run manadger, this would mean get rid of the comfig
# The other alternative is to see that we have multiple env that we resample every time
# TODO: Make juste an env type (so that is accomodates for not only 2 d env// different transmats)
# TODO: Make The plotting in the general plotting utilse