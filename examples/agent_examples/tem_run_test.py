import matplotlib.pyplot as plt
import numpy as np

from neuralplayground.agents import Whittington2020
from neuralplayground.arenas import BatchEnvironment
from neuralplayground.arenas import DiscreteObjectEnvironment
from neuralplayground.backend import tem_training_loop
from neuralplayground.backend import SingleSim

from neuralplayground.agents.whittington_2020_extras import whittington_2020_parameters as parameters
from neuralplayground.experiments import Sargolini2006Data

from neuralplayground.agents import Stachenfeld2018
from neuralplayground.arenas import Simple2D
from neuralplayground.backend import episode_based_training_loop

simulation_id = "TEM_custom_sim"
agent_class = Whittington2020
env_class = BatchEnvironment
training_loop = tem_training_loop

params = parameters.parameters()
full_agent_params = params.copy()

arena_x_limits = [[-5,5], [-4,4], [-5,5], [-6,6], [-4,4], [-5,5], [-6,6], [-5,5], [-4,4], [-5,5], [-6,6], [-5,5], [-4,4], [-5,5], [-6,6], [-5,5]]
arena_y_limits = [[-5,5], [-4,4], [-5,5], [-6,6], [-4,4], [-5,5], [-6,6], [-5,5], [-4,4], [-5,5], [-6,6], [-5,5], [-4,4], [-5,5], [-6,6], [-5,5]]
room_widths = [10, 8, 10, 12, 8, 10, 12, 10, 8, 10, 12, 10, 8, 10, 12, 10]
room_depths = [10, 8, 10, 12, 8, 10, 12, 10, 8, 10, 12, 10, 8, 10, 12, 10]

env_params = {"environment_name": "BatchEnvironment",
              "env_class": DiscreteObjectEnvironment,
              "batch_size": 16,
              "arena_x_limits": arena_x_limits,
              "arena_y_limits": arena_y_limits,
              "state_density": 1,
              "n_objects": params["n_x"],
              "agent_step_size": 1,
              "use_behavioural_data": False,
              "data_path": None,
              "experiment_class": Sargolini2006Data}
agent_params = {"model_name": "SimpleTEM",
                "params": full_agent_params,
                "batch_size": 16,
                "room_widths": room_widths,
                "room_depths": room_depths,
                "state_densities": [1]*16,
                "use_behavioural_data": False}

training_loop_params = {"n_episode": 3, "params": full_agent_params}

sim = SingleSim(simulation_id = simulation_id,
                agent_class = agent_class,
                agent_params = agent_params,
                env_class = env_class,
                env_params = env_params,
                training_loop = training_loop,
                training_loop_params = training_loop_params)

# print(sim)
print("Running sim...")
sim.run_sim()