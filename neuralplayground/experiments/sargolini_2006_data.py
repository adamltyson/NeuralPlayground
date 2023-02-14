import os.path
import numpy as np
import scipy.io as sio
import glob
import neuralplayground
from neuralplayground.experiments import Hafting2008Data
from neuralplayground.utils import clean_data
from neuralplayground.experiments import Experiment


class SargoliniDataTrajectory(Experiment):
    """ Data class for sargolini et al. 2006. https://www.science.org/doi/10.1126/science.1125572
        The data can be obtained from https://archive.norstore.no/pages/public/datasetDetail.jsf?id=8F6BE356-3277-475C-87B1-C7A977632DA7
        This class only consider animal trajectory pre-processed by the authors.
    """

    def __init__(self, experiment_name: str = 'Sargolini_2006_Data', data_path: str = None):
        """ SargoliniData Class Init

        Parameters
        ----------
        experiment_name: str
            string to identify object in case of multiple instances
        data_path: str
            if None, load the data sample in the package, load the specific dataset otherwise
        """
        self.experiment_name = experiment_name
        if data_path is None:
            # Set data_path to the data directory within the package
            self.data_path = os.path.join(neuralplayground.__path__[0], "experiments/sargolini_2006")
        else:
            self.data_path = data_path
        # Sort the data in data_path
        self.arena_limits, self.position, self.head_direction, self.time_span = self._get_sargolini_data()

    def _get_sargolini_data(self, tolerance: float = 1e-10):
        """ Load and concatenate animal trajectories from data pre-processed by the authors

        Parameters
        ----------
        tolerance: float
            Small constant to avoid dividing by zero when estimating head direction

        Returns
        -------
        arena_limits: ndarray (2, 2)
            first row x limits of the arena, second row y limits of the arena, in cm
        position: ndarray (n, 2)
            first column is x pos in cm, second column is y pos in cm, n is the number of sampled positions
        head_direction: ndarray (n-1, 2)
            directional vector with estimated head direction from position derivative
        time_span: ndarray (n, )
            time stamp per measurement assuming 50Hz of sampling rate
        """
        # Arena limits in cm, sampling rate in Hz, both from the original experiment
        arena_limits = np.array([[-50, 50], [-50, 50]])
        self.sampling_rate = 50

        # Listing files with trajectories
        filenames_x = os.path.join(self.data_path, "sargolini_x_pos_")
        filenames_y = os.path.join(self.data_path, "sargolini_y_pos_")

        # Filing array from files
        x_position = np.array([])
        y_position = np.array([])
        for i in range(61):
            aux_x = np.load(filenames_x + str(i) + ".npy")
            aux_y = np.load(filenames_y + str(i) + ".npy")
            x_position = np.concatenate([x_position, aux_x])
            y_position = np.concatenate([y_position, aux_y])

        position = np.stack([x_position, y_position], axis=1) * 100  # Convert to cm, originally in meters
        head_direction = np.diff(position, axis=0)  # Head direction from derivative of position
        head_direction = head_direction/np.sqrt(np.sum(head_direction**2, axis=1) + tolerance)[..., np.newaxis]
        time_span = np.arange(head_direction.shape[0])*(1/self.sampling_rate)
        return arena_limits, position, head_direction, time_span


class Sargolini2006Data(Hafting2008Data):
    """ Data class for sargolini et al. 2006. https://www.science.org/doi/10.1126/science.1125572
        The data can be obtained from https://archive.norstore.no/pages/public/datasetDetail.jsf?id=8F6BE356-3277-475C-87B1-C7A977632DA7
        This class only consider animal raw animal trajectories and neural recordings
    """
    def __init__(self, data_path=None, recording_index=None, experiment_name="FullSargoliniData", verbose=False):
        super().__init__(data_path=data_path, recording_index=recording_index,
                         experiment_name=experiment_name, verbose=verbose)

    def _find_data_path(self, data_path):
        if data_path is None:
            self.data_path = os.path.join(neuralplayground.__path__[0], "experiments/sargolini_2006/raw_data_sample/")
        else:
            self.data_path = data_path

    def _load_data(self):
        self.best_recording_index = 0
        # self.best_session = {"rat_id": "10704", "session": "20060402"}
        self.arena_limits = np.array([[-50.0, 50.0], [-50.0, 50.0]])

        data_path_list = glob.glob(self.data_path + "*.mat")
        mice_ids = np.unique([dp.split("/")[-1][:5] for dp in data_path_list])
        self.data_per_animal = {}
        for m_id in mice_ids:
            m_paths_list = glob.glob(self.data_path + m_id + "*.mat")
            sessions = np.unique([dp.split("/")[-1].split("-")[1][:8] for dp in m_paths_list]).astype(str)
            self.data_per_animal[m_id] = {}
            for sess in sessions:
                s_paths_list = glob.glob(self.data_path + m_id + "-" + sess + "*.mat")
                cell_ids = np.unique([dp.split("/")[-1].split(".")[-2][-4:] for dp in s_paths_list]).astype(str)
                self.data_per_animal[m_id][sess] = {}
                for cell_id in cell_ids:
                    if cell_id == "_POS":
                        session_info = "position"
                    elif cell_id in ["_EEG", "_EGF"]:
                        session_info = cell_id[1:]
                    else:
                        session_info = cell_id
                    r_path = glob.glob(self.data_path + m_id + "-" + sess + "*" + cell_id + "*.mat")
                    cleaned_data = clean_data(sio.loadmat(r_path[0]))
                    if cell_id != "_POS" and not cell_id in ["_EEG", "_EGF"]:
                        try:
                            self.data_per_animal[m_id][sess][session_info] = cleaned_data["cellTS"]
                        except:
                            pass
                    else:
                        self.data_per_animal[m_id][sess][session_info] = cleaned_data

    def get_tetrode_data(self, session_data=None, tetrode_id=None):
        if session_data is None:
            session_data, rev_vars, rat_info = self.get_recording_data(recording_index=0)
            tetrode_id = self._find_tetrode(rev_vars)
        position_data = session_data["position"]
        x1, y1 = position_data["posx"][:, 0], position_data["posy"][:, 0]
        x2, y2 = x1, y1
        # Selecting positional data
        x = np.clip(x2, a_min=self.arena_limits[0, 0], a_max=self.arena_limits[0, 1])
        y = np.clip(y2, a_min=self.arena_limits[1, 0], a_max=self.arena_limits[1, 1])
        time_array = position_data["post"][:]
        tetrode_data = session_data[tetrode_id]
        test_spikes = tetrode_data[:, 0]
        time_array = time_array[:, 0]
        return time_array, test_spikes, x, y


if __name__ == "__main__":

    # print("initializing hafting")
    # data = FullHaftingData(verbose=True)
    # print("plotting_tragectory")
    # data.plot_trajectory(2)
    # print("plotting_recording")
    # data.plot_recording_tetr(2)
    # plt.show()

    print("initializing sargolini")
    # data = FullSargoliniData(verbose=True)
    # print("plotting_tragectory")
    # data.plot_trajectory(2)
    # print("plotting_recording")
    # data.plot_recording_tetr(2)
    # plt.show()







