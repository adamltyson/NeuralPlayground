"""
From https://doi.org/10.1016/j.cub.2015.02.037
"""

import numpy as np
from .simple2d import Simple2D


class ConnectedRooms(Simple2D):
    """
    Simulation from https://doi.org/10.1016/j.cub.2015.02.037
    Grid Cells Form a Global Representation of Connected Environments
    """
    def __init__(self, environment_name="ConnectedRooms", corridor_ysize=40.0, singleroom_ysize=90.0,
                 singleroom_xsize=90, door_size=10.0, **env_kwargs):
        """
        Parameters
        ----------
        environment_name : string
            name of the environment
        corridor_ysize : float
            corridor size from the paper, default 40.0 cm
        singleroom_ysize : float
            y-size of one of the rooms, default 90.0 cm
        singleroom_xsize : float
            x-size of one of the rooms, default 90.0 cm
        door_size : float
            door size from room to corridor, default 10 cm
        env_kwargs
        """

        self.corridor_ysize = corridor_ysize
        self.singleroom_ysize = singleroom_ysize
        self.singleroom_xsize = singleroom_xsize
        self.door_size = door_size

        env_kwargs["arena_x_limits"] = np.array([-self.singleroom_xsize, self.singleroom_xsize])
        env_kwargs["arena_y_limits"] = np.array([-self.singleroom_ysize, self.corridor_ysize])

        super().__init__(environment_name, **env_kwargs)

    def _create_custom_walls(self):
        self.custom_walls = []
        # Walls from limit

        self.custom_walls.append(np.array([[0, 0], [0, -self.singleroom_ysize]]))
        self.custom_walls.append(np.array([[-self.singleroom_xsize, 0], [-(self.singleroom_xsize/2+self.door_size/2), 0]]))
        self.custom_walls.append(np.array([[-(self.singleroom_xsize/2-self.door_size/2), 0], [0, 0]]))
        self.custom_walls.append(np.array([[0, 0], [self.singleroom_xsize/2-self.door_size/2, 0]]))
        self.custom_walls.append(np.array([[self.singleroom_xsize/2+self.door_size/2, 0], [self.singleroom_xsize, 0]]))