"""
Define the class CornerKickFinder
Author : Chloe Gobe
Date : 20.05.2023
"""

from math import sqrt
import pandas as pd
import numpy as np
import pickle
import os
from tqdm import tqdm
from match_toolbox import Match

pd.set_option("mode.chained_assignment", None)

def linear_interpolation(data):
    values = np.array(data, dtype=float)
    indices = np.arange(len(values))
    valid_indices = np.where(~np.isnan(values))
    
    if np.sum(valid_indices) == 0:
        # Toutes les valeurs sont None, aucune interpolation possible
        return [None] * len(data)
    
    interpolated = np.interp(indices, valid_indices[0], values[valid_indices])
    
    # Remplacer les None par les valeurs interpolées
    interpolated_data = data.copy()
    for i, val in enumerate(interpolated_data):
        if val is None:
            interpolated_data[i] = interpolated[i]
    
    return interpolated_data


class CornerKickFinder:
    """
    Define the class CornerKickFinder whose purpose is to
    find the starting frame of potentiel corner kicks situations
    """

    def __init__(self, match_id: int):
        self.match_id = match_id
        self.match = Match(match_id)
        self.match.gather_information()
        self.df_tracking = self.match.df_tracking[
            ~self.match.df_tracking["time"].isna()
        ]
        self.df_potential = pd.DataFrame()

    def _corner_coordinates(self) -> tuple:
        length, width = self.match.pitch_size
        return [
            (x, y)
            for x in (length / 2, -1 * length / 2)
            for y in (width / 2, -1 * width / 2)
        ]

    def _is_in_circle(
        self, x: float, y: float, a: float, b: float, rayon: float
    ) -> bool:
        distance = sqrt((x - a) ** 2 + (y - b) ** 2)
        return distance < rayon

    def _is_in_corner_coin(self, x: float, y: float) -> bool:
        if x is None and y is None:
            return False
        return any(
            self._is_in_circle(x, y, corner[0], corner[1], 1)
            for corner in self._corner_coordinates()
        )

    def check_players_coordinatess_in_circle(
        self, players_coordinates: pd.DataFrame, coin: tuple
    ) -> bool:
        """
        Check if there is two opponents in a 10 yards circle around the corners of the field

        Args:
        ------
            players_coordinates (pd.DataFrame): the coordinates of the players_coordinates
            coin (tuple): coordinates of a corner

        Returns:
        -------
            bool
        """
        # Filter players_coordinatess inside the circle
        players_coordinates["distance"] = np.sqrt(
            (players_coordinates["x"] - coin[0]) ** 2
            + (players_coordinates["y"] - coin[1]) ** 2
        )
        filtered_df = players_coordinates[
            players_coordinates["distance"] <= 10 * 0.9144
        ]

        # Check if there are two players_coordinatess from different teams inside the circle
        teams = filtered_df["team"].unique()
        if len(teams) <= 1:
            return True  # There is one team present inside the circle or None
        else:
            return False  # There are two different teams present inside the circle


    def find_potentiel_corner_kicks(self):
        """
        Find the starting frames of potentiel corner kicks candidates
        """
        # First check if the analysis has not yet been done, otherwise load the pickle
        if os.path.exists(f"pickle/{self.match_id}.pkl"):
            with open(f"pickle/{self.match_id}.pkl", "rb") as file:
                self.df_potential = pickle.load(file)
            print(
                f"{self.match_id} : Already found potentiel corner kicks - loading is over"
            )

        else:
            self.df_potential = self.match.df_tracking[
                ~self.match.df_tracking["time"].isna()
            ]
            # List the frames where the conditions meet
            list_frames = []

            for frame in tqdm(self.df_potential["frame"].to_list()):
                (
                    players_coordinates,
                    ball_coordinates,
                    _,
                ) = self.match.get_coordinates_from_frame(frame)

                # If there is an empty frame continue to the next frame
                if (len(players_coordinates) == 0) or (players_coordinates.empty):
                    continue

                # If the ball is visible, get its location, otherwise the condition is False
                if ball_coordinates is not None:
                    condition_on_ball = (
                        self._is_in_corner_coin(  # Corner coin ?
                            ball_coordinates["x"], ball_coordinates["y"]
                        )
                        and ball_coordinates.get("z", 0) < 0.2
                    )  # Throw in ?
                else:
                    # If the ball is not visible we are going to do a linear interpolation
                    # of its positions 30 frames before and after the frame to see if we can find something
                    x_gps = []
                    y_gps=[]
                    for idx in range(frame-50, frame+50):
                        _, ball_gps, _ = self.match.get_coordinates_from_frame(idx)
                        if ball_gps is not None:
                            x_gps.append(ball_gps["x"])
                            y_gps.append(ball_gps["y"])
                        else:
                            x_gps.append(None)
                            y_gps.append(None)
                    
                    # Interpolation
                    y_gps = linear_interpolation(y_gps)
                    x_gps = linear_interpolation(x_gps)
                    
                    condition_on_ball = any(
                        self._is_in_corner_coin(a, b) for a, b in zip(x_gps, y_gps))

                # Is there a player on the corner of the field ?
                condition_on_players_coordinates = (
                    sum(
                        players_coordinates.apply(
                            lambda x: self._is_in_corner_coin(x["x"], x["y"]), axis=1
                        )
                    )
                    != 0
                )

                # Does the situation abide by the law of distance of the defenders ?
                condition_on_distance_limit = any(
                    [
                        self.check_players_coordinatess_in_circle(
                            players_coordinates, center
                        )
                        for center in self._corner_coordinates()
                    ]
                )

                # If the frame is a candidate, save it
                if (
                    condition_on_ball or condition_on_players_coordinates
                ) and condition_on_distance_limit:
                    list_frames.append(frame)

            # Filter the potentiel with the frames that respect the condition
            self.df_potential = self.df_potential[
                self.df_potential["frame"].isin(list_frames)
            ][["frame", "time"]]

            # To be detected as a new situation
            self.df_potential = self.df_potential[
                self.df_potential["frame"].diff() > 10
            ]

            # Save the file if needed
            with open(f"pickle/{self.match_id}.pkl", "wb") as file:
                pickle.dump(self.df_potential, file)


if __name__ == "__main__":
    for idf in tqdm([2068, 2269, 2417, 2440, 2841, 3442, 3518, 3749, 4039]):
        print(f"Processing match : {idf}")
        analyzer = CornerKickFinder(match_id=idf)
        analyzer.find_potentiel_corner_kicks()
