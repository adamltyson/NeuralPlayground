import sys

sys.path.append("../")
import numpy as np
import random
from model.core import NeuralResponseModel as NeurResponseModel
import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np
from scipy.stats import multivariate_normal
from environments.env_list.simple2d import Simple2D, Sargolini2006
from tqdm import tqdm


class ExcInhPlasticity(NeurResponseModel):

    def __init__(self, model_name="ExcitInhibitoryplastic", **mod_kwargs):
        super().__init__(model_name, **mod_kwargs)
        self.agent_step_size = mod_kwargs["agent_step_size"]
        self.metadata = {"mod_kwargs": mod_kwargs}
        self.etaexc = mod_kwargs["exc_eta"]  # Learning rate.
        self.etainh = mod_kwargs["inh_eta"]
        self.Ne = mod_kwargs["Ne"]
        self.Ni = mod_kwargs["Ni"]
        self.Nef = mod_kwargs["Nef"]
        self.Nif = mod_kwargs["Nif"]

        self.sigma_exc = mod_kwargs["sigma_exc"]

        self.sigma_inh = mod_kwargs["sigma_inh"]
        self.room_width, self.room_depth = mod_kwargs["room_width"], mod_kwargs["room_depth"]
        self.ro = mod_kwargs["ro"]
        self.obs_history = []

        self.resolution = 50
        self.x_array = np.linspace(-self.room_width/2, self.room_width/2, num=self.resolution)
        self.y_array = np.linspace(-self.room_depth/2, self.room_depth/2, num=self.resolution)
        self.mesh = np.array(np.meshgrid(self.x_array, self.y_array))
        self.xy_combinations = self.mesh.T.reshape(-1, 2)

        self.reset()

    def reset(self):
        self.global_steps = 0
        self.history = []
        self.wi = np.random.normal(loc=1.52, scale=1.52*0.05, size=(self.Ni))  # what is the mu and why do we have the 1 and not2
        self.we = np.random.normal(loc=1.0, scale=1.0*0.05, size=(self.Ne))

        self.inh_rates_functions, self.inh_cell_list = self.generate_tuning_curves(n_curves=self.Ni,
                                                                                   cov_scale=self.sigma_inh,
                                                                                   Nf=self.Nif)
        self.exc_rates_functions, self.exc_cell_list = self.generate_tuning_curves(n_curves=self.Ne,
                                                                                   cov_scale=self.sigma_exc,
                                                                                   Nf=self.Nef)
        self.init_we_sum = np.sum(self.we**2)

    def generate_tuning_curves(self, n_curves, cov_scale, Nf):
        width_limit = self.room_width / 2.0
        depth_limit = self.room_depth / 2.0
        cell_list = []
        function_list = []
        for i in tqdm(range(n_curves)):
            gauss_list = []
            cell_i = 0
            for j in range(Nf):
                mean1 = np.random.uniform(-width_limit*(1+0.1), width_limit*(1+0.1))
                mean2 = np.random.uniform(-depth_limit*(1+0.1), depth_limit*(1+0.1))
                cov = np.diag([(self.room_width * cov_scale)**2, (self.room_depth * cov_scale)**2])
                mean = [mean1, mean2]
                rv = multivariate_normal(mean, cov)
                function_list.append([mean, cov])
                cell_i += rv.pdf(self.xy_combinations)
            function_list.append(gauss_list)
            norm_cell_i = (cell_i - np.amin(cell_i))/np.amax((cell_i - np.amin(cell_i)))
            cell_list.append(norm_cell_i)
        return function_list, np.array(cell_list)

    def act(self, obs):
        self.obs_history.append(obs)
        action = np.random.normal(scale=0.1, size=(2,))
        return action

    def get_output_rates(self, pos):
        exc_rates = self.get_rates(self.exc_cell_list, pos)
        inh_rates = self.get_rates(self.inh_cell_list, pos)

        r_out = self.we.T @ exc_rates - self.wi.T @ inh_rates
        # print("debug")
        return np.abs(r_out)

    def get_rates(self, cell_list, pos, get_n_cells=None):
        diff = self.xy_combinations - pos[np.newaxis, ...]
        dist = np.sum(diff**2, axis=1)
        index = np.argmin(dist)
        rout = []
        for i in range(cell_list.shape[0]):
            rout.append(cell_list[i, index])
        return np.abs(rout)

    def get_full_output_rate(self):
        r_out = self.we.T @ self.exc_cell_list - self.wi.T @ self.inh_cell_list
        r_out = r_out.reshape((self.resolution, self.resolution))
        r_out = np.abs(r_out)
        return np.abs(r_out)

    def update(self, exc_normalization=True):
        pos = self.obs_history[-1]
        r_out = self.get_output_rates(pos)

        delta_we = self.etaexc*self.get_rates(self.exc_cell_list, pos=pos)
        delta_wi = self.etainh*self.get_rates(self.inh_cell_list, pos=pos)*(r_out - self.ro)

        # print(delta_wi, delta_we)

        self.we = self.we + delta_we
        self.wi = self.wi + delta_wi

        if exc_normalization:
            self.we = self.init_we_sum/np.sum(self.we**2)*self.we

        self.we = np.abs(self.we)
        self.wi = np.abs(self.wi)

    def plot_rates(self):
        f, ax = plt.subplots(1, 3, figsize=(14, 5))

        r_out_im = self.get_full_output_rate()
        exc_im = self.exc_cell_list[0, ...].reshape((self.resolution, self.resolution))
        inh_im = self.inh_cell_list[0, ...].reshape((self.resolution, self.resolution))

        ax[0].imshow(exc_im, cmap="Reds")
        ax[0].set_title("Exc rates", fontsize=14)
        ax[1].imshow(inh_im, cmap="Blues")
        ax[1].set_title("Inh rates", fontsize=14)
        im = ax[2].imshow(r_out_im)
        ax[2].set_title("Out rate", fontsize=14)
        cbar = plt.colorbar(im, ax=ax[2])
        plt.show()


if __name__ == "__main__":
    # Create an env
    data_path = "/home/rodrigo/HDisk/8F6BE356-3277-475C-87B1-C7A977632DA7_1/all_data/"

    session = {"rat_id": "11016", "sess": "31010502"}

    env = Sargolini2006(data_path=data_path,
                        verbose=False,
                        session=session,
                        time_step_size=None,
                        agent_step_size=None)

    exc_eta = 2e-5
    inh_eta = 8e-5
    model_name = "model_example"
    sigma_exc = 0.05
    sigma_inh = 0.1
    Ne = 4900
    Ni = 1225
    Nef = 100
    Nif = 100
    agent_step_size = 0.1

    print("init cells")
    agent = ExcInhPlasticity(model_name=model_name, exc_eta=exc_eta, inh_eta=inh_eta, sigma_exc=sigma_exc,
                             sigma_inh=sigma_inh, Ne=Ne, Ni=Ni, agent_step_size=agent_step_size, ro=1,
                             Nef=Nef, Nif=Nif, room_width=env.room_width, room_depth=env.room_depth)
    print("Plotting rate")
    agent.plot_rates()

    print("running updates")
    n_steps = 30000
    # Initialize environment
    obs, state = env.reset()
    for i in tqdm(range(n_steps)):
        # Observe to choose an action
        obs = obs[:2]
        action = agent.act(obs)
        rate = agent.update()
        # Run environment for given action
        obs, state, reward = env.step(action)

    print("plotting results")
    agent.plot_rates()