# TODO: NOTE to self: This is a work in progress, it has not been tested to work, I think Jax is not a good way to implement in object oriented coding.
# I think if I want to implement it here I should use neuralplayground it would be in pytorch.

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
from neuralplayground.agents.agent_core import AgentCore

os.environ["KMP_DUPLICATE_LIB_OK"] = "True"
from neuralplayground.agents.domine_2023_extras.class_Graph_generation import sample_padded_grid_batch_shortest_path
from neuralplayground.agents.domine_2023_extras.class_grid_run_config import GridConfig
from neuralplayground.agents.domine_2023_extras.class_models import get_forward_function
from neuralplayground.agents.domine_2023_extras.class_plotting_utils import (
    plot_graph_grid_activations,
    plot_input_target_output,
    plot_message_passing_layers,
    plot_xy,
)
from neuralplayground.agents.domine_2023_extras.class_utils import rng_sequence_from_rng, set_device
from sklearn.metrics import matthews_corrcoef, roc_auc_score


class Domine2023(AgentCore,):


    def __init__ (  # autogenerated
        self,
        #agent_name: str = "SR",
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
        self.obs_history = []
        self.grad_history = []
        self.train_on_shortest_path = train_on_shortest_path
        self.experiment_name = experiment_name
        self.train_on_shortest_path = train_on_shortest_path
        self.resample = resample
        self.wandb_on = wandb_on
        self.seed = seed

        self.feature_position = feature_position
        self.weighted = weighted

        self.num_hidden = num_hidden
        self.num_layers = num_layers
        self.num_message_passing_steps = num_message_passing_steps
        self.learning_rate = learning_rate
        self.num_training_steps = num_training_steps
        # cconfig.num_training_steps  # @param

        self.batch_size =batch_size
        self.nx_min = nx_min
        self.nx_max = nx_max

        # This can be tought of the brain making different rep of different  granularity
        # Could be explained during sleep
        self.batch_size_test = batch_size_test
        self.nx_min_test = nx_min_test  # This is thought of the state density
        self.nx_max_test = nx_max_test   # This is thought of the state density
        self.batch_size = batch_size
        self.nx_min = nx_min   # This is thought of the state density
        self.nx_max = nx_max

        self.arena_x_limits = mod_kwargs["arena_y_limits"]
        self.arena_y_limits = mod_kwargs["arena_y_limits"]
        self.room_width = np.diff(self.arena_x_limits)[0]
        self.room_depth = np.diff(self.arena_y_limits)[0]
        self.agent_step_size = 0

        self.log_every = num_training_steps // 10
        if self.weighted:
            self.edge_lables = True
        else:
            self.edge_lables = False

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

        self.reset()
        self.saving_run_parameters()

        rng = jax.random.PRNGKey(self.seed)
        self.rng_seq = rng_sequence_from_rng(rng)


        if self.train_on_shortest_path:
            self.graph, self.targets = sample_padded_grid_batch_shortest_path(
                rng, self.batch_size, self.feature_position, self.weighted, self.nx_min, self.nx_max
            )
        else:
            self.graph, self.targets = sample_padded_grid_batch_shortest_path(
                rng, self.batch_size, self.feature_position, self.weighted, self.nx_min, self.nx_max
            )
        forward = get_forward_function(self.num_hidden, self.num_layers, self.num_message_passing_steps)
        net_hk = hk.without_apply_rng(hk.transform(forward))
        params = net_hk.init(rng, self.graph)
        self.params = params
        optimizer = optax.adam(self.learning_rate)
        opt_state = optimizer.init(self.params)
        self.opt_state = opt_state

        def compute_loss(params, inputs, targets):
            outputs = net_hk.apply(params, inputs)
            return jnp.mean((outputs[0].nodes - targets) ** 2)  # using MSE

        self._compute_loss = jax.jit(compute_loss)

        def update_step(params,opt_state):
            loss, grads = jax.value_and_grad(compute_loss)(
                params, self.graph, self.targets
            )  # jits inside of value_and_grad
            updates, opt_state = optimizer.update(grads, opt_state,params)
            params = optax.apply_updates(params, updates)
            return params, opt_state ,loss

        self._update_step = jax.jit(update_step)

        def evaluate(params, inputs, target, Target_Value):
            outputs = net_hk.apply(params, inputs)
            if Target_Value:
                roc_auc = roc_auc_score(np.squeeze(target), np.squeeze(outputs[0].nodes))
            else:
                roc_auc = False
            MCC = matthews_corrcoef(np.squeeze(target), round(np.squeeze(outputs[0].nodes)))
            return outputs, roc_auc, MCC

        self._evaluate = evaluate


    def saving_run_parameters(self):

        path = os.path.join(self.save_path, "run.py")
        HERE = os.path.join(Path(os.getcwd()).resolve(), "domine_2023.py")
        shutil.copyfile(HERE, path)

        path = os.path.join(self.save_path, "class_Graph_generation.py")
        HERE = os.path.join(Path(os.getcwd()).resolve(), "domine_2023_extras/class_Graph_generation.py")
        shutil.copyfile(HERE, path)

        path = os.path.join(self.save_path, "class_utils.py")
        HERE = os.path.join(Path(os.getcwd()).resolve(), "domine_2023_extras/class_utils.py")
        shutil.copyfile(HERE, path)

        path = os.path.join(self.save_path, "class_plotting_utils.py")
        HERE = os.path.join(Path(os.getcwd()).resolve(), "domine_2023_extras/class_plotting_utils.py")
        shutil.copyfile(HERE, path)

        path = os.path.join(self.save_path, "class_config_run.yaml")
        HERE = os.path.join(Path(os.getcwd()).resolve(), "domine_2023_extras/class_config.yaml")
        shutil.copyfile(HERE, path)

    def reset(self,a=1):
        self.obs_history = []  # Initialize observation history to update weights later
        self.grad_history = []
        self.global_steps = 0
        self.losses = []
        self.losses_test = []
        self.losses_wse = []
        self.losses_test_wse = []
        self.roc_aucs_train = []
        self.MCCs_train = []
        self.MCCs_test = []
        self.roc_aucs_test = []
        self.MCCs_train_wse = []
        self.MCCs_test_wse = []
        return

    def update(self):
        rng = next(self.rng_seq)
        if self.train_on_shortest_path:
            graph_test, target_test = sample_padded_grid_batch_shortest_path(
                rng, self.batch_size_test, self.feature_position, self.weighted, self.nx_min_test, self.nx_max_test
                    )
            rng = next(self.rng_seq)

            if self.resample:
                self.graph, self.targets = sample_padded_grid_batch_shortest_path(
                    rng, self.batch_size, self.feature_position, self.weighted, self.nx_min, self.nx_max
                )
        else:
            graph_test, target_test= sample_padded_grid_batch_shortest_path(
                rng, self.batch_size_test, self.feature_position, self.weighted, self.nx_min_test, self.nx_max_test
            )
            target_test =  np.reshape(graph_test.nodes[:, 0], (graph_test.nodes[:, 0].shape[0], -1))

            rng = next(self.rng_seq)
            #target_test_wse = target_test - graph_test.nodes[:, 0]
            if self.resample:
                self.graph, self.targets= sample_padded_grid_batch_shortest_path(
                    rng, self.batch_size, self.feature_position, self.weighted, self.nx_min, self.nx_max
                )
            self.targets = np.reshape(self.graph.nodes[:, 0], (self.graph.nodes[:, 0].shape[0], -1)) #self.graph.nodes[:,0]
            #target_wse = self.targets - self.graph.nodes[:, 0]

        if self.feature_position:
            target_test_wse = target_test - np.reshape(graph_test.nodes[:, 0], (graph_test.nodes[:, 0].shape[0], -1))
            target_wse = self.targets - np.reshape(self.graph.nodes[:, 0], (self.graph.nodes[:, 0].shape[0], -1))
        else:
            target_test_wse = target_test - graph_test.nodes[:]
            target_wse = self.targets - self.graph.nodes[:]

        # Train
        self.params,self.opt_state, loss = self._update_step(self.params,self.opt_state )
        self.losses.append(loss)
        outputs_train, roc_auc_train, MCC_train = self._evaluate(self.params, self.graph, self.targets, True)
        self.roc_aucs_train.append(roc_auc_train)
        self.MCCs_train.append(MCC_train)

        # Train without end start in the target
        loss_wse = self._compute_loss(self.params, self.graph, target_wse)
        self.losses_wse.append(loss_wse)
        outputs_train_wse, roc_auc_train_wse, MCC_train_wse = self._evaluate(self.params, self.graph, target_wse, False)
        self.MCCs_train_wse.append(MCC_train_wse)

        # Test
        loss_test = self._compute_loss(self.params,graph_test, target_test)
        self.losses_test.append(loss_test)
        outputs_test, roc_auc_test, MCC_test = self._evaluate(self.params, graph_test, target_test, True)
        self.roc_aucs_test.append(roc_auc_test)
        self.MCCs_test.append(MCC_test)

        # Test without end start in the target
        loss_test_wse = self._compute_loss(self.params, graph_test, target_test_wse)
        self.losses_test_wse.append(loss_test_wse)
        outputs_test_wse, roc_auc_test_wse, MCC_test_wse = self._evaluate(self.params, graph_test, target_test_wse, False)
        self.MCCs_test_wse.append(MCC_test_wse)

        # Log
        wandb_logs = {"loss": loss, "losses_test": loss_test, "roc_auc_test": roc_auc_test, "roc_auc": roc_auc_train}
        if self.wandb_on:
            wandb.log(wandb_logs)
        self.global_steps = self.global_steps + 1
        if self.global_steps % self.log_every == 0:
            print(f"Training step {self.global_steps}: loss = {loss} , loss_test = {loss_test}, roc_auc_test = {roc_auc_test}, roc_auc_train = {roc_auc_train}")
        return

    def print_and_plot(self):
        # EVALUATE
        rng = next(self.rng_seq)
        if self.train_on_shortest_path:
            graph_test, target_test = sample_padded_grid_batch_shortest_path(
                rng, self.batch_size_test, self.feature_position, self.weighted, self.nx_min_test, self.nx_max_test
                    )
        else:
            rng = next(self.rng_seq)
            graph_test, target_test = sample_padded_grid_batch_shortest_path(
                rng, self.batch_size_test, self.feature_position, self.weighted, self.nx_min_test, self.nx_max_test
            )
            target_test = np.reshape(graph_test.nodes[:, 0], (graph_test.nodes[:, 0].shape[0], -1))

        if self.feature_position:
            target_test_wse = target_test - np.reshape(graph_test.nodes[:, 0], (graph_test.nodes[:, 0].shape[0], -1))
            target_wse = self.targets - np.reshape(self.graph.nodes[:, 0], (self.graph.nodes[:, 0].shape[0], -1))
        else:
            target_test_wse = target_test - graph_test.nodes[:]
            target_wse = self.targets - self.graph.nodes[:]


        outputs_test, roc_auc_test, MCC_test = self._evaluate(self.params, graph_test, target_test, True)
        outputs_test_wse, roc_auc_test_wse, MCC_test_wse = self._evaluate(self.params, graph_test, target_test_wse, False)
        outputs, roc_auc, MCC = self._evaluate(self.params, self.graph, self.targets, True)
        outputs_wse, roc_auc_wse, MCC_wse = self._evaluate(self.params, self.graph,  target_wse , False)

        # SAVE PARAMETER (NOT WE SAVE THE FILES SO IT SHOULD BE THERE AS WELL )
        if self.wandb_on:
            with open("readme.txt", "w") as f:
                f.write("readme")
            with open(os.path.join(self.save_path, "Constant.txt"), "w") as outfile:
                outfile.write("num_message_passing_steps" + str(self.num_message_passing_steps) + "\n")
                outfile.write("Learning_rate:" + str(self.learning_rate) + "\n")
                outfile.write("num_training_steps:" + str(self.num_training_steps))
                outfile.write("roc_auc" + str(roc_auc_test))
                outfile.write("MCC" + str(MCC_test))
                outfile.write("roc_auc_wse" + str(roc_auc_test_wse))
                outfile.write("MCC_wse" + str(MCC_test_wse))

        # PLOTTING THE LOSS and AUC ROC
        plot_xy(self.losses, os.path.join(self.save_path, "Losses.pdf"), "Losses")
        plot_xy(self.losses_test, os.path.join(self.save_path, "Losses_test.pdf"), "Losses_test")

        plot_xy(self.losses_wse, os.path.join(self.save_path, "Losses_wse.pdf"), "Losses_wse")
        plot_xy(self.losses_test_wse, os.path.join(self.save_path, "Losses_test_wse.pdf"), "Losses_test_wse")

        plot_xy(self.roc_aucs_test, os.path.join(self.save_path, "auc_roc_test.pdf"), "auc_roc_test")
        plot_xy(self.roc_aucs_train, os.path.join(self.save_path, "auc_roc_train.pdf"), "auc_roc_train")

        plot_xy(self.MCCs_train, os.path.join(self.save_path, "MCC_train.pdf"), "MCC_train")
        plot_xy(self.MCCs_test, os.path.join(self.save_path, "MCC_test.pdf"), "MCC_test")

        plot_xy(self.MCCs_train_wse, os.path.join(self.save_path, "MCC_train_wse.pdf"), "MCC_train_wse")
        plot_xy(self.MCCs_test_wse, os.path.join(self.save_path, "MCC_test_wse.pdf"), "MCC_test_wse")

        # PLOTTING ACTIVATION FOR TEST AND THE TARGET OF THE THING ( NOTE THAT IS WAS TRANED ON THE ALL THING)
        plot_input_target_output(
            list(graph_test.nodes.sum(-1)),
            target_test.sum(-1),
            outputs_test[0].nodes.tolist(),
            graph_test,
            4,
            self.edge_lables,
            os.path.join(self.save_path, "in_out_targ_test.pdf"),
        )
        plot_message_passing_layers(
            list(graph_test.nodes.sum(-1)),
            outputs_test[1],
            target_test.sum(-1),
            outputs_test[0].nodes.tolist(),
            graph_test,
            3,
            self.num_message_passing_steps,
            self.edge_lables,
            os.path.join(self.save_path, "message_passing_graph_test.pdf"),
        )

        plot_input_target_output(
            list(graph_test.nodes.sum(-1)),
            target_test_wse.sum(-1),
            outputs_test_wse[0].nodes.tolist(),
            graph_test,
            4,
            self.edge_lables,
            os.path.join(self.save_path, "in_out_targ_test_wse.pdf"),
        )

        # Train
        # PLOTTING ACTIVATION OF THE FIRST 2 GRAPH OF THE BATCH
        plot_input_target_output(
            list(self.graph.nodes.sum(-1)),
            self.targets.sum(-1),
            outputs[0].nodes.tolist(),
            self.graph,
            4,
            self.edge_lables,
            os.path.join(self.save_path, "in_out_targ_train.pdf"),
        )

        plot_input_target_output(
            list(self.graph.nodes.sum(-1)),
            target_wse.sum(-1),
            outputs_wse[0].nodes.tolist(),
            self.graph,
            4,
            self.edge_lables,
            os.path.join(self.save_path, "in_out_targ_train_wse.pdf"),
        )


        # graph_test, target_test = sample_padded_grid_batch_shortest_path(
        #  rng, self.batch_size_test, self.feature_position, self.weighted, self.nx_min_test, self.nx_max_test
        #  )
        # graph_test= self.graph
        # target_test = self.targets

        # plot_message_passing_layers_units(outputs[1], target_test.sum(-1), outputs[0].nodes.tolist(),graph_test,config.num_hidden,config.num_message_passing_steps,edege_lables,os.path.join(save_path, 'message_passing_hidden_unit.pdf'))

        # Plot each seperatly
        # plot_graph_grid_activations(
        #      outputs[0].nodes.tolist(),
        #      graph_test,
        #      os.path.join(self.save_path, "outputs_test.pdf"),
        #     "Predicted Node Assignments with GCN test",
        #     self.edge_lables,
        # )
        # plot_graph_grid_activations(
        #    list(graph_test.nodes.sum(-1)),
        #   graph_test,
        #     os.path.join(self.save_path, "Inputs_test.pdf"),
        #    "Inputs node assigments test ",
        #     self.edge_lables,
        #  )
        #  plot_graph_grid_activations(
        #     target_test.sum(-1), graph_test, os.path.join(self.save_path, "Target_test.pdf"), "Target_test", self.edge_lables
        #  )


        # PLOTTING ACTIVATION OF THE FIRST 2 GRAPH OF THE BATCHe
        plot_input_target_output(
            list( self.graph.nodes.sum(-1)),
            target_wse.sum(-1),
            outputs_wse[0].nodes.tolist(),
            self.graph,
            4,
            self.edge_lables,
            os.path.join(self.save_path, "in_out_targ_train_wse.pdf"),
        )

        plot_message_passing_layers(
            list( self.graph.nodes.sum(-1)),
            outputs_wse[1],
            target_wse.sum(-1),
            outputs_wse[0].nodes.tolist(),
            self.graph,
            3,
            self.num_message_passing_steps,
            self.edge_lables,
            os.path.join(self.save_path, "message_passing_graph_train_wse.pdf"),
        )

        plot_input_target_output(
            list( self.graph.nodes.sum(-1)),
            self.targets.sum(-1),
            outputs[0].nodes.tolist(),
            self.graph,
            4,
            self.edge_lables,
            os.path.join(self.save_path, "in_out_targ_train.pdf"),
        )

        plot_message_passing_layers(
            list( self.graph.nodes.sum(-1)),
            outputs[1],
            self.targets.sum(-1),
            outputs[0].nodes.tolist(),
            self.graph,
            3,
            self.num_message_passing_steps,
            self.edge_lables,
            os.path.join(self.save_path, "message_passing_graph_train.pdf"),
        )
        # plot_message_passing_layers_units(outputs[1], target_test.sum(-1), outputs[0].nodes.tolist(),graph_test,config.num_hidden,config.num_message_passing_steps,edege_lables,os.path.join(save_path, 'message_passing_hidden_unit.pdf'))

        # Plot each seperatly
        #  plot_graph_grid_activations(
        #   outputs[0].nodes.tolist(),
        #    graph_test,
        #   os.path.join(self.save_path, "outputs_train.pdf"),
        #   "Predicted Node Assignments with GCN",
        #   self.edge_lables,
        #   )
        #  plot_graph_grid_activations(
        #    list(graph_test.nodes.sum(-1)),
        #    graph_test,
        #    os.path.join(self.save_path, "Inputs_train.pdf"),
        #      "Inputs node assigments",
        #   self.edge_lables,
        #  )
        # plot_graph_grid_activations(
        #  target_test.sum(-1), graph_test, os.path.join(self.save_path, "Target_train.pdf"), "Target", self.edge_lables
        # )        print('End')

if __name__ == "__main__":
    from neuralplayground.arenas import Simple2D

    # @title Graph net functions
    parser = argparse.ArgumentParser()
    parser.add_argument(
    "--config_path",
    metavar="-C",
    default="domine_2023_extras/class_config.yaml",
    help="path to base configuration file.",
)

    args = parser.parse_args()
    set_device()
    config_class = GridConfig
    config = config_class(args.config_path)


    # Init environment
    arena_x_limits = [-100, 100]
    arena_y_limits = [-100, 100]
    #env = Simple2D
    #   time_step_size=time_step_size,
    #  agent_step_size=agent_step_size,
    #  arena_x_limits=arena_x_limits,
    #   arena_y_limits=arena_y_limits,
    # )

    agent = Domine2023( experiment_name=config.experiment_name,
    train_on_shortest_path= config.train_on_shortest_path,
    resample= config.resample,  # @param
    wandb_on= config.wandb_on,
    seed= config.seed,
    feature_position= config.feature_position,
    weighted= config.weighted,
    num_hidden= config.num_hidden,  # @param
    num_layers= config.num_layers,  # @param
    num_message_passing_steps= config.num_message_passing_steps,  # @param
    learning_rate= config.learning_rate  ,  # @param
    num_training_steps= config.num_training_steps,  # @param
    batch_size= config.batch_size,
    nx_min= config.nx_min,
    nx_max= config. nx_max,
    batch_size_test= config.batch_size_test,
    nx_min_test= config.nx_min_test,
    nx_max_test= 7,arena_y_limits=arena_y_limits, arena_x_limits=arena_x_limits
    )

    for n in range(config.num_training_steps):
        agent.update()
    agent.print_and_plot()

# TODO: Run manadger (not possible for now), to get a seperated code we would juste need to change the paths and config this would mean get rid of the comfig
# The other alternative is to see that we have multiple env that we resample every time
# TODO: Make juste an env type (so that is accomodates for not only 2 d env// different transmats)
# TODO: Make The plotting in the general plotting utilse
#if __name__ == "__main__":
#  x = Domine2023()
    # x = x.replace(obs_history=[1, 2], num_hidden=2)
    # x.num_hidden = 5
    #
    #  x.update()