import argparse
import os
import shutil
from datetime import datetime
from pathlib import Path
import haiku as hk
import jax
import jax.ops as jop
import jax.numpy as jnp
import optax
import wandb
from sklearn.metrics import matthews_corrcoef, roc_auc_score
from neuralplayground.agents.agent_core import AgentCore

os.environ["KMP_DUPLICATE_LIB_OK"] = "True"
from neuralplayground.agents.domine_2023_extras.class_Graph_generation import (
    sample_padded_batch_graph,
)
from neuralplayground.agents.domine_2023_extras.class_grid_run_config import GridConfig
from neuralplayground.agents.domine_2023_extras.class_models import get_forward_function
from neuralplayground.agents.domine_2023_extras.class_plotting_utils import (
    plot_input_target_output,
    plot_message_passing_layers,
    plot_curves,
)
from neuralplayground.agents.domine_2023_extras.class_utils import (
    rng_sequence_from_rng,
    set_device,
    update_outputs_test,
    get_length_shortest_path,
)



#TODO: Implement all in Neuralplayground
class Domine2023(
    AgentCore,
):
    def __init__(  # autogenerated
        self,
        # agent_name: str = "SR",
        experiment_name="smaller size generalisation graph with  no position feature",
        train_on_shortest_path: bool = True,
        resample: bool = True,
        wandb_on: bool = False,
        seed: int = 41,
        feature_position: bool = False,
        weighted: bool = True,
        num_hidden: int = 100,
        num_layers: int = 2,
        num_message_passing_steps: int = 3,
        learning_rate: float = 0.001,
        num_training_steps: int = 10,
        residual=True,
        layer_norm=True,
        batch_size: int = 4,
        nx_min: int = 4,
        nx_max: int = 7,
        batch_size_test: int = 4,
        nx_min_test: int = 4,
        nx_max_test: int = 7,
        grid: bool= True,
        plot: bool= True,
        dist_cutoff=10,
        n_std_dist_cutoff=5,

        **mod_kwargs,
    ):

        self.grid = grid
        self.plot = plot
        self.obs_history = []
        self.grad_history = []
        self.train_on_shortest_path = train_on_shortest_path
        self.experiment_name = experiment_name
        self.resample = resample
        self.wandb_on = wandb_on
        self.dist_cutoff = dist_cutoff ,
        self.n_std_dist_cutoff= n_std_dist_cutoff,

        self.seed = seed
        self.feature_position = feature_position
        self.weighted = weighted

        self.num_hidden = num_hidden
        self.num_layers = num_layers
        self.num_message_passing_steps = num_message_passing_steps
        self.learning_rate = learning_rate
        self.num_training_steps = num_training_steps

        # This can be tought of the brain making different rep of different  granularity
        # Could be explained during sleep
        self.batch_size_test = batch_size_test
        self.nx_min_test = nx_min_test  # This is thought of the state density
        self.nx_max_test = nx_max_test  # This is thought of the state density
        self.batch_size = batch_size
        self.nx_min = nx_min  # This is thought of the state density
        self.nx_max = nx_max

        self.arena_x_limits = mod_kwargs["arena_y_limits"]
        self.arena_y_limits = mod_kwargs["arena_y_limits"]
        self.agent_step_size = 0
        self.residuals = residual
        self.layer_norm = layer_norm

        self.log_every = num_training_steps // 10
        if self.weighted:
            self.edge_lables = True
        else:
            self.edge_lables = True

        if self.wandb_on:
            dateTimeObj = datetime.now()
            wandb.init(
                project="graph-delaunay_2",
                entity="graph-brain",
                name=experiment_name + dateTimeObj.strftime("%d%b_%H_%M_%S"),
            )
            self.wandb_logs = {}
            save_path = wandb.run.dir
            os.mkdir(os.path.join(save_path, "results"))
            self.save_path = os.path.join(save_path, "results")
        self.reset()

        rng = jax.random.PRNGKey(self.seed)
        self.rng_seq = rng_sequence_from_rng(rng)

        if self.train_on_shortest_path:
            self.graph, self.targets = sample_padded_batch_graph(
                rng,
                self.batch_size,
                self.feature_position,
                self.weighted,
                self.nx_min,
                self.nx_max,
                self.grid,
                self.dist_cutoff[0],
                self.n_std_dist_cutoff[0],
            )
            rng = next(self.rng_seq)
            self.graph_test, self.target_test = sample_padded_batch_graph(
                rng,
                self.batch_size_test,
                self.feature_position,
                self.weighted,
                self.nx_min_test,
                self.nx_max_test,
                self.grid,
                self.dist_cutoff[0],
                self.n_std_dist_cutoff[0],
            )

        else:
            self.graph_test, self.target_test = sample_padded_batch_graph(
                rng,
                self.batch_size_test,
                self.feature_position,
                self.weighted,
                self.nx_min_test,
                self.nx_max_test,
                self.grid,
                self.dist_cutoff[0],
                self.n_std_dist_cutoff[0],
            )
            self.target_test = jnp.reshape(
                self.graph_test.nodes[:, 0], (self.graph_test.nodes[:, 0].shape[0], -1)
            )
            rng = next(self.rng_seq)
            self.graph, self.targets = sample_padded_batch_graph(
                rng,
                self.batch_size,
                self.feature_position,
                self.weighted,
                self.nx_min,
                self.nx_max,
                self.grid,
                self.dist_cutoff[0],
                self.n_std_dist_cutoff[0],
            )
            self.targets = jnp.reshape(
                self.graph.nodes[:, 0], (self.graph.nodes[:, 0].shape[0], -1)
            )

        if self.feature_position:
            self.indices_train = jnp.where(self.graph.nodes[:] == 1)[0]
            self.indices_test = jnp.where(self.graph_test.nodes[:, 0] == 1)[0]

            self.target_test_wse = self.target_test - jnp.reshape(
                self.graph_test.nodes[:, 0], (self.graph_test.nodes[:, 0].shape[0], -1)
            )
            self.target_wse = self.targets - jnp.reshape(
                self.graph.nodes[:, 0], (self.graph.nodes[:, 0].shape[0], -1)
            )
        else:
            self.indices_train = jnp.where(self.graph.nodes[:] == 1)[0]
            self.indices_test = jnp.where(self.graph_test.nodes[:] == 1)[0]
            self.target_test_wse = self.target_test - self.graph_test.nodes[:]
            self.target_wse = self.targets - self.graph.nodes[:]

        forward = get_forward_function(
            self.num_hidden,
            self.num_layers,
            self.num_message_passing_steps,
            self.residuals,
            self.layer_norm,
        )

        net_hk = hk.without_apply_rng(hk.transform(forward))
        params = net_hk.init(rng, self.graph)
        param_count = sum(x.size for x in jax.tree_util.tree_leaves(params))
        print("Total number of parameters: %d" % param_count)
        self.params = params
        optimizer = optax.adam(self.learning_rate)
        opt_state = optimizer.init(self.params)
        self.opt_state = opt_state

        def compute_loss(params, graph, targets):
            outputs = net_hk.apply(params, graph)
            return jnp.mean((outputs[0].nodes - targets) ** 2)

        self._compute_loss = jax.jit(compute_loss)

        def compute_loss_per_node(params, graph, targets):
            outputs = net_hk.apply(params, graph)
            return (outputs[0].nodes - targets) ** 2

        self._compute_loss_per_node = jax.jit(compute_loss_per_node)

        def compute_loss_per_graph(params, graph, targets):
            outputs = net_hk.apply(params, graph)
            node_features = jnp.squeeze(targets)  # n_node_total x n_feat
            # graph id for each node
            i = int(0)
            for n in graph.n_node:
                if i == 0:
                    graph_ids = jnp.zeros(n) + i
                else:
                    graph_id = jnp.zeros(n) + i
                    graph_ids = jnp.concatenate([graph_ids, graph_id], axis=0)
                i = i + 1
            graph_ids = jnp.concatenate(
                [jnp.zeros(n) + i for i, n in enumerate(graph.n_node)], axis=0
            )
            assert graph_ids.shape[0] == node_features.shape[0]
            summed_outputs = jop.segment_sum(outputs[0].nodes, graph_ids.astype(int))
            summed_node_features = jop.segment_sum(node_features, graph_ids.astype(int))
            assert summed_node_features.shape[0] == graph.n_node.shape[0]
            denom = graph.n_node
            denom = jnp.where(denom == 0, 1, denom)
            mean_node_features = summed_node_features / denom
            mean_outputs = jnp.squeeze(summed_outputs) / denom
            return (mean_node_features - mean_outputs) ** 2
        self._compute_loss_per_graph = compute_loss_per_graph

        def compute_loss_nodes_shortest_path(params, graph, targets):
            outputs = net_hk.apply(params, graph)
            node_features = jnp.squeeze(targets)  # n_node_total x n_feat
            # graph id for each node
            i = int(0)
            for n in graph.n_node:
                if i == 0:
                    graph_ids = jnp.zeros(n) + i
                else:
                    graph_id = jnp.zeros(n) + i
                    graph_ids = jnp.concatenate([graph_ids, graph_id], axis=0)
                i = i + 1

            graph_ids = graph_ids + (jnp.squeeze(targets * i))
            denom = [jnp.size(jnp.where(graph_ids[:] ==  n)) for n in range((len(graph.n_node)-1)*2+1)]
            denom= jnp.asarray(denom)
            denom = jnp.where(denom == 0, 1, denom)
            assert graph_ids.shape[0] == node_features.shape[0]
            summed_outputs = jnp.squeeze(
                jop.segment_sum(outputs[0].nodes, graph_ids.astype(int))
            )
            summed_node_features = jop.segment_sum(node_features, graph_ids.astype(int))
            mean_summed_outputs = summed_outputs /denom
            mean_summed_node_features=summed_node_features / denom

            return (mean_summed_outputs - mean_summed_node_features) ** 2  # np.concatenate((np.squeeze(loss_per_graph),np.asarray(len_shortest_path)),axis=0)
        self._compute_loss_nodes_shortest_path = compute_loss_nodes_shortest_path

        def update_step(params, opt_state):
            loss, grads = jax.value_and_grad(compute_loss)(
                params, self.graph, self.targets
            )  # jits inside of value_and_grad
            updates, opt_state = optimizer.update(grads, opt_state, params)
            params = optax.apply_updates(params, updates)
            return params, opt_state, loss
        self._update_step = jax.jit(update_step)

        def evaluate(params, inputs, target, wse_value=True, indices=None):
            outputs = net_hk.apply(params, inputs)
            if wse_value:
                roc_auc = roc_auc_score(
                    jnp.squeeze(target), jnp.squeeze(outputs[0].nodes)
                )
                MCC = matthews_corrcoef(
                    jnp.squeeze(target), round(jnp.squeeze(outputs[0].nodes))
                )
            else:
                output = outputs[0].nodes
                for ind in indices:
                    output = output.at[ind].set(0)

                MCC = matthews_corrcoef(jnp.squeeze(target), round(jnp.squeeze(output)))
                roc_auc = False

            return outputs, roc_auc, MCC

        self._evaluate = evaluate

        wandb_logs = {
            "train_on_shortest_path": train_on_shortest_path,
            "resample": resample,
            "batch_size_test": batch_size_test,
            "nx_min_test": nx_min_test,  # This is thought of the state density
            "nx_max_test": nx_max_test,  # This is thought of the state density
            "batch_size": batch_size,
            "nx_min": nx_min,  # This is thought of the state density
            "nx_max": nx_max,
            "seed": seed,
            "feature_position": feature_position,
            "weighted": weighted,
            "num_hidden": num_hidden,
            "num_layers": num_layers,
            "num_message_passing_steps": num_message_passing_steps,
            "learning_rate": learning_rate,
            "num_training_steps": num_training_steps,
            "param_count": param_count,
            "residual": residual,
            "layer_norm": layer_norm,
        }

        if self.wandb_on:
            wandb.log(wandb_logs)

        else:
            dateTimeObj = datetime.now()
            save_path = os.path.join(Path(os.getcwd()).resolve(), "results")
            os.mkdir(
                os.path.join(
                    save_path,
                    self.experiment_name + dateTimeObj.strftime("%d%b_%H_%M_%S"),
                )
            )
            self.save_path = os.path.join(
                os.path.join(
                    save_path,
                    self.experiment_name + dateTimeObj.strftime("%d%b_%H_%M_%S"),
                )
            )
        self.saving_run_parameters()

    def saving_run_parameters(self):
        path = os.path.join(self.save_path, "run.py")
        HERE = os.path.join(Path(os.getcwd()).resolve(), "domine_2023.py")
        shutil.copyfile(HERE, path)

        path = os.path.join(self.save_path, "class_Graph_generation.py")
        HERE = os.path.join(
            Path(os.getcwd()).resolve(), "domine_2023_extras/class_Graph_generation.py"
        )
        shutil.copyfile(HERE, path)

        path = os.path.join(self.save_path, "class_utils.py")
        HERE = os.path.join(
            Path(os.getcwd()).resolve(), "domine_2023_extras/class_utils.py"
        )
        shutil.copyfile(HERE, path)

        path = os.path.join(self.save_path, "class_plotting_utils.py")
        HERE = os.path.join(
            Path(os.getcwd()).resolve(), "domine_2023_extras/class_plotting_utils.py"
        )
        shutil.copyfile(HERE, path)

        path = os.path.join(self.save_path, "class_config_run.yaml")
        HERE = os.path.join(
            Path(os.getcwd()).resolve(), "domine_2023_extras/class_config.yaml"
        )
        shutil.copyfile(HERE, path)

    def reset(self, a=1):
        self.obs_history = []  # Initialize observation history to update weights later
        self.grad_history = []
        self.global_steps = 0
        self.losses_train = []
        self.losses_test = []
        self.log_losses_per_node_test = []
        self.log_losses_per_graph_test = []
        self.log_losses_per_shortest_path_test = []
        self.losses_train_wse = []
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
        if self.resample:
            if self.train_on_shortest_path:
                self.graph, self.targets = sample_padded_batch_graph(
                    rng,
                    self.batch_size,
                    self.feature_position,
                    self.weighted,
                    self.nx_min,
                    self.nx_max,
                    self.grid,
                    self.dist_cutoff,
                    self.n_std_dist_cutoff[0],
                )
            else:
                rng = next(self.rng_seq)
                # Sample
                self.graph, self.targets = sample_padded_batch_graph(
                    rng,
                    self.batch_size,
                    self.feature_position,
                    self.weighted,
                    self.nx_min,
                    self.nx_max,
                    self.grid,
                    self.dist_cutoff,
                    self.n_std_dist_cutoff[0],
                )
                self.targets = jnp.reshape(
                    self.graph.nodes[:, 0], (self.graph.nodes[:, 0].shape[0], -1)
                )

            if self.feature_position:
                self.indices_train = jnp.where(self.graph.nodes[:] == 1)[0]
                self.target_wse = self.targets - jnp.reshape(
                    self.graph.nodes[:, 0], (self.graph.nodes[:, 0].shape[0], -1)
                )
            else:
                self.indices_train = jnp.where(self.graph.nodes[:] == 1)[0]
                self.target_wse = self.targets - self.graph.nodes[:]

        # Train
        self.params, self.opt_state, loss = self._update_step(
            self.params, self.opt_state
        )
        self.losses_train.append(loss)
        self.outputs_train, roc_auc_train, MCC_train = self._evaluate(
            self.params, self.graph, self.targets, True
        )
        self.roc_aucs_train.append(roc_auc_train)
        self.MCCs_train.append(MCC_train)

        # Train without end start in the target
        loss_wse = self._compute_loss(self.params, self.graph, self.target_wse)
        self.losses_train_wse.append(loss_wse)
        outputs_train_wse_wrong, roc_auc_train_wse, MCC_train_wse = self._evaluate(
            self.params, self.graph, self.target_wse, False, self.indices_train
        )
        self.outputs_train_wse = update_outputs_test(
            outputs_train_wse_wrong, self.indices_train
        )
        self.MCCs_train_wse.append(MCC_train_wse)

        # Test
        loss_test_per_node = self._compute_loss_per_node(
            self.params, self.graph_test, self.target_test
        )
        loss_test_per_graph = self._compute_loss_per_graph(
            self.params, self.graph_test, self.target_test
        )
        loss_nodes_shortest_path = self._compute_loss_nodes_shortest_path(
            self.params, self.graph_test, self.target_test
        )
        self.log_losses_per_node_test.append(jnp.log(jnp.squeeze(loss_test_per_node)))
        self.log_losses_per_graph_test.append(jnp.log(loss_test_per_graph))
        self.log_losses_per_shortest_path_test.append(jnp.log(loss_nodes_shortest_path))

        loss_test = self._compute_loss(self.params, self.graph_test, self.target_test)
        self.losses_test.append(loss_test)
        self.outputs_test, roc_auc_test, MCC_test = self._evaluate(
            self.params, self.graph_test, self.target_test, True
        )
        self.roc_aucs_test.append(roc_auc_test)
        self.MCCs_test.append(MCC_test)

        # Test without end start in the target
        loss_test_wse = self._compute_loss(
            self.params, self.graph_test, self.target_test_wse
        )
        self.losses_test_wse.append(loss_test_wse)
        outputs_test_wse_wrong, roc_auc_test_wse, MCC_test_wse = self._evaluate(
            self.params, self.graph_test, self.target_test_wse, False, self.indices_test
        )
        self.outputs_test_wse = update_outputs_test(
            outputs_test_wse_wrong, self.indices_test
        )
        self.MCCs_test_wse.append(MCC_test_wse)

        # Log
        wandb_logs = {
            "loss_test_per_node": jnp.log(jnp.squeeze(loss_test_per_node)),
            "log_loss_test": jnp.log(loss_test),
            "log_loss_test_wse": jnp.log(loss_test_wse),
            "log_loss": jnp.log(loss),
            "log_loss_wse": jnp.log(loss_wse),
            "roc_auc_test": roc_auc_test,
            "roc_auc_test_wse": roc_auc_test_wse,
            "roc_auc_train": roc_auc_train,
            "roc_auc_train_wse": roc_auc_train_wse,
            "MCC_test": MCC_test,
            "MCC_test_wse": MCC_test_wse,
            "MCC_train": MCC_train,
            "MCC_train_wse": MCC_train_wse,
        }
        if self.wandb_on:
            wandb.log(wandb_logs)
        self.global_steps = self.global_steps + 1
        if self.global_steps % self.log_every == 0:
            # if self.plot == True:
            # Uncomment if one wants to plot the activation at different time points
            # self.plot_learning_curves(str(self.global_steps))
            # self.plot_activation(str(self.global_steps))
            print(
                f"Training step {self.global_steps}: log_loss = {jnp.log(loss)} , log_loss_test = {jnp.log(loss_test)}, roc_auc_test = {roc_auc_test}, roc_auc_train = {roc_auc_train}"
            )

        if self.global_steps == self.num_training_steps:
            if self.wandb_on:
                with open("readme.txt", "w") as f:
                    f.write("readme")
                with open(os.path.join(self.save_path, "Constant.txt"), "w") as outfile:
                    outfile.write(
                        "num_message_passing_steps"
                        + str(self.num_message_passing_steps)
                        + "\n"
                    )
                    outfile.write("Learning_rate:" + str(self.learning_rate) + "\n")
                    outfile.write(
                        "num_training_steps:" + str(self.num_training_steps) + "\n"
                    )
                    outfile.write("roc_auc" + str(roc_auc_test) + "\n")
                    outfile.write("MCC" + str(MCC_test) + "\n")
                    outfile.write("roc_auc_wse" + str(roc_auc_test_wse) + "\n")
                    outfile.write("MCC_wse" + str(MCC_test_wse) + "\n")
                wandb.finish()
            if self.plot == True:
                print("Plotting and Saving Figures")
                self.plot_learning_curves(str(self.global_steps))
                self.plot_activation(str(self.global_steps))

        return

    def plot_learning_curves(self, trainning_step):
        plot_curves(
            [
                self.losses_train,
                self.losses_test,
                self.losses_train_wse,
                self.losses_test_wse,
            ],
            os.path.join(self.save_path, "Losses_" + trainning_step + ".pdf"),
            "All_Losses",
            legend_labels=["loss", "loss test", "loss_wse", "loss_test_wse"],
        )

        plot_curves(
            [
                jnp.log(jnp.asarray(self.losses_train)),
                jnp.log(jnp.asarray(self.losses_test)),
                jnp.log(jnp.asarray(self.losses_train_wse)),
                jnp.log(jnp.asarray(self.losses_test_wse)),
            ],
            os.path.join(self.save_path, "Log_Losses_" + trainning_step + ".pdf"),
            "All_log_Losses",
            legend_labels=[
                "log_loss",
                "log_loss test",
                "log_loss_wse",
                "log_loss_test_wse",
            ],
        )

        plot_curves(
            [self.losses_train],
            os.path.join(self.save_path, "Losses_train_" + trainning_step + ".pdf"),
            "Losses",
        )
        plot_curves(
            [self.losses_test],
            os.path.join(self.save_path, "losses_test_" + trainning_step + ".pdf"),
            "losses_test",
        )

        transposed_list = [list(item) for item in zip(*self.log_losses_per_node_test)]
        plot_curves(
            transposed_list,
            os.path.join(
                self.save_path, "Log_Losses_per_node_test_" + trainning_step + ".pdf"
            ),
            "Log_Losse_per_node",
        )
        transposed_list = [list(item) for item in zip(*self.log_losses_per_graph_test)]

        plot_curves(
            transposed_list,
            os.path.join(
                self.save_path, "Log_Losses_per_graph_test_" + trainning_step + ".pdf"
            ),
            "Log_Loss_per_graph " ,
            ["GRAPH" + str(n) for n in range(self.batch_size_test + 1)],
        )

        transposed_list = [
            list(item) for item in zip(*self.log_losses_per_shortest_path_test)
        ]
        shortest_path_length = get_length_shortest_path(self.graph_test, self.target_test)

        plot_curves(
            [self.losses_train_wse],
            os.path.join(self.save_path, "Losses_wse_" + trainning_step + ".pdf"),
            "Losses_wse",
        )
        plot_curves(
            [self.losses_test_wse],
            os.path.join(self.save_path, "losses_test_wse_" + trainning_step + ".pdf"),
            "losses_test_wse",
        )
        plot_curves(
            transposed_list,
            os.path.join(
                self.save_path, "Log_Loss_on_shortest_path" + trainning_step + ".pdf"),
            "Log_Loss_on shortest_path",
            ["Other_node graph" + str(n) for n in range(self.batch_size_test + 1)]+
             ["SHORTEST_PATH graph_len_" + str(shortest_path_length[n]) + "graph_size" + str(p) for n, p in
               enumerate(self.graph_test.n_node[:-1])])

        plot_curves(
            [self.roc_aucs_test, self.roc_aucs_train],
            os.path.join(self.save_path, "auc_rocs_" + trainning_step + ".pdf"),
            "All_auc_roc",
            legend_labels=["auc_roc_test", "auc_roc_train_" + trainning_step + ".pdf"],
        )
        plot_curves(
            [self.roc_aucs_test],
            os.path.join(self.save_path, "auc_roc_test_" + trainning_step + ".pdf"),
            "auc_roc_test",
        )
        plot_curves(
            [self.roc_aucs_train],
            os.path.join(self.save_path, "auc_roc_train_" + trainning_step + ".pdf"),
            "auc_roc_train",
        )

        plot_curves(
            [self.MCCs_train, self.MCCs_test, self.MCCs_train_wse, self.MCCs_test_wse],
            os.path.join(self.save_path, "MCCs_" + trainning_step + ".pdf"),
            "All_MCCs",
            legend_labels=["MCC", "MCC test", "MCC_wse", "MCC_test_wse"],
        )
        plot_curves(
            [self.MCCs_train],
            os.path.join(self.save_path, "MCC_train_" + trainning_step + ".pdf"),
            "MCC_train",
        )
        plot_curves(
            [self.MCCs_test],
            os.path.join(self.save_path, "MCC_test_" + trainning_step + ".pdf"),
            "MCC_test",
        )
        plot_curves(
            [self.MCCs_train_wse],
            os.path.join(self.save_path, "MCC_train_wse_" + trainning_step + ".pdf"),
            "MCC_train_wse",
        )
        plot_curves(
            [self.MCCs_test_wse],
            os.path.join(self.save_path, "MCC_test_wse_" + trainning_step + ".pdf"),
            "MCC_test_wse",
        )

    def plot_activation(self, trainning_step):
        # PLOTTING ACTIVATION FOR TEST AND THE TARGET OF THE THING ( NOTE THAT IS WAS TRANED ON THE ALL THING)
        plot_input_target_output(
            list(self.graph_test.nodes.sum(-1)),
            self.target_test.sum(-1),
            jnp.squeeze(self.outputs_test[0].nodes).tolist(),
            self.graph_test,
            2,
            self.edge_lables,
            os.path.join(self.save_path, "in_out_targ_test_" + trainning_step + ".pdf"),
            "in_out_targ_test",
        )

        new_vector = [1 if val > 0.3 else 0 for val in self.outputs_test[0].nodes]
        plot_input_target_output(
            list(self.graph_test.nodes.sum(-1)),
            self.target_test.sum(-1),
            new_vector,
            self.graph_test,
            2,
            self.edge_lables,
            os.path.join(
                self.save_path, "in_out_targ_test_threshold_" + trainning_step + ".pdf"
            ),
            "in_out_targ_test",
        )

        plot_message_passing_layers(
            list(self.graph_test.nodes.sum(-1)),
            self.outputs_test[1],
            self.target_test.sum(-1),
            jnp.squeeze(self.outputs_test[0].nodes).tolist(),
            self.graph_test,
            2,
            self.num_message_passing_steps,
            self.edge_lables,
            os.path.join(
                self.save_path,
                "message_passing_graph_test.pdf",
            ),
            "message_passing_graph_test",
        )

        plot_input_target_output(
            list(self.graph_test.nodes.sum(-1)),
            self.target_test_wse.sum(-1),
            jnp.squeeze(self.outputs_test_wse).tolist(),
            self.graph_test,
            2,
            self.edge_lables,
            os.path.join(
                self.save_path, "in_out_targ_test_wse_" + trainning_step + ".pdf"
            ),
            "in_out_targ_test_wse",
        )

        # Train
        # PLOTTING ACTIVATION OF THE FIRST 2 GRAPH OF THE BATCH
        new_vector = [1 if val > 0.3 else 0 for val in self.outputs_train[0].nodes]
        plot_input_target_output(
            list(self.graph.nodes.sum(-1)),
            self.targets.sum(-1),
            new_vector,
            self.graph,
            2,
            self.edge_lables,
            os.path.join(
                self.save_path, "in_out_targ_train_threshold_" + trainning_step + ".pdf"
            ),
            "in_out_targ_train",
        )

        plot_input_target_output(
            list(self.graph.nodes.sum(-1)),
            self.target_wse.sum(-1),
            jnp.squeeze(self.outputs_train_wse).tolist(),
            self.graph,
            2,
            self.edge_lables,
            os.path.join(
                self.save_path, "in_out_targ_train_wse_" + trainning_step + ".pdf"
            ),
            "in_out_targ_train_wse",
        )

        plot_input_target_output(
            list(self.graph.nodes.sum(-1)),
            self.targets.sum(-1),
            jnp.squeeze(self.outputs_train[0].nodes).tolist(),
            self.graph,
            2,
            self.edge_lables,
            os.path.join(
                self.save_path, "in_out_targ_train_" + trainning_step + ".pdf"
            ),
            "in_out_targ_train",
        )

        plot_message_passing_layers(
            list(self.graph.nodes.sum(-1)),
            self.outputs_train[1],
            self.targets.sum(-1),
            jnp.squeeze(self.outputs_train[0].nodes).tolist(),
            self.graph,
            2,
            self.num_message_passing_steps,
            self.edge_lables,
            os.path.join(
                self.save_path, "message_passing_graph_train_" + trainning_step + ".pdf"
            ),
            "message_passing_graph_train",
        )

    print("End")


if __name__ == "__main__":
    from neuralplayground.arenas import Simple2D

    # @title Graph net functions
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config_path",
        metavar="-C",
        default="domine_2023_extras/class_config_base.yaml",
        help="path to base configuration file.",
    )

    args = parser.parse_args()
    set_device()
    config_class = GridConfig
    config = config_class(args.config_path)

    # Init environment
    arena_x_limits = [-100, 100]
    arena_y_limits = [-100, 100]

    agent = Domine2023(
        experiment_name=config.experiment_name,
        train_on_shortest_path=config.train_on_shortest_path,
        resample=config.resample,  # @param
        wandb_on=config.wandb_on,
        seed=config.seed,
        feature_position=config.feature_position,
        weighted=config.weighted,
        num_hidden=config.num_hidden,  # @param
        num_layers=config.num_layers,  # @param
        num_message_passing_steps=config.num_message_passing_steps,  # @param
        learning_rate=config.learning_rate,  # @param
        num_training_steps=config.num_training_steps,  # @param
        batch_size=config.batch_size,
        nx_min=config.nx_min,
        nx_max=config.nx_max,
        batch_size_test=config.batch_size_test,
        nx_min_test=config.nx_min_test,
        nx_max_test=config.nx_max_test,
        arena_y_limits=arena_y_limits,
        arena_x_limits=arena_x_limits,
        residual=config.residual,
        layer_norm=config.layer_norm,
        grid = config.grid,
        plot = config.plot,
         dist_cutoff=config.dist_cutoff,
        n_std_dist_cutoff= config.n_std_dist_cutoff,
    )

    for n in range(config.num_training_steps):
        agent.update()
