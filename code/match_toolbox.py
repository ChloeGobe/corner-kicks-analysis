"""
Define the class Match
Author : Chloe Gobe
Date : 20.05.2023
"""

import json
import pandas as pd
from tqdm import tqdm
import imageio
import os
import matplotlib.pyplot as plt
from IPython.display import display, Image
from code.pitch import plot_pitch

def extract_values(row):
    return pd.Series(row['data'])

class Match:
    """
    Define the class Match to load and get all the needed data
    and information to analyze the games
    """

    def __init__(self, match_id: int):
        self.match_id = match_id
        self.match_data = None
        self.df_tracking = None
        self.teams = None
        self.df_teams = None
        self.df_players = None
        self.pitch_size = (None, None)
        self.id_referee = None
        self.id_ball = None

    def _load_match_data(self):
        with open(
            f"data/matches/{self.match_id}/match_data.json", "r", encoding="utf-8"
        ) as file:
            self.match_data = json.load(file)

    def _load_tracking_data(self):
        self.df_tracking = pd.read_json(
            f"data/matches/{self.match_id}/structured_data.json"
        )
        default_value = (
            {"y": None, "x": None, "trackable_object": None, "track_id": None},
        )
        self.df_tracking["data"] = self.df_tracking["data"].apply(
            lambda x: default_value if x == [] else x
        )

    def _get_team_info(self):
        self.teams = {
            "home_team": self.match_data["home_team"]
            | self.match_data["home_team_kit"],
            "away_team": self.match_data["away_team"]
            | self.match_data["away_team_kit"],
        }
        self.df_teams = pd.DataFrame.from_dict(self.teams, orient="index")
        self.df_teams = self.df_teams.reset_index()
        self.df_teams.rename(columns={"index": "team"}, inplace=True)

    def _get_players_info(self):
        self.df_players = pd.DataFrame(self.match_data["players"])[
            ["number", "first_name", "last_name", "trackable_object", "team_id"]
        ]

    def _get_referees_id(self):
        self.id_referee = [x["trackable_object"] for x in self.match_data["referees"]]

    def _get_ball_id(self):
        self.id_ball = self.match_data["ball"]["trackable_object"]

    def _get_pitch_dimensions(self):
        self.pitch_size = (
            self.match_data["pitch_length"],
            self.match_data["pitch_width"],
        )

    def gather_information(self):
        """
        Use all the methods to collect information about the game
        and load it into the object
        """
        self._load_match_data()
        self._load_tracking_data()
        self._get_team_info()
        self._get_players_info()
        self._get_referees_id()
        self._get_ball_id()
        self._get_pitch_dimensions()


    # _________________________________________________________________

    def _is_in_boxes(self, x:float, y:float) ->bool:
        """
        Check how many players in the box

        Args:
            x (float): _description_
            y (float): _description_

        Returns:
            bool: _description_
        """
        length, _ = self.pitch_size
        area_width = 44 * 0.9144
        area_length = 18 * 0.9144
        condition_y = -area_width/2 < y < area_width/2
        condition_x_left = -length/2 < x < -length/2 + area_length
        condition_x_right = length/2 > x > length/2 - area_length
        return condition_y and (condition_x_right or condition_x_left)
    

    def count_players_in_box(self, frame_id:int)->tuple:
        df_players, _, _ = self.get_coordinates_from_frame(frame_id)
        df_players["in_box"] = df_players.apply(lambda x : self._is_in_boxes(x["x"], x["y"]), axis=1)
        home_players = df_players[df_players["team"] == "home_team"]["in_box"].sum()
        away_players = df_players[df_players["team"] == "away_team"]["in_box"].sum()
        return home_players, away_players

    # ____________________FRAME SPECIFIC METHODS_______________________

    def get_coordinates_from_frame(self, frame_id: int):
        """
        From a given frame, take all the positions of the players,
        the referee, the ball and give the time.

        Args:
            frame_id (int): identifier of a frame

        Returns:
            df_player_coordinates : pandas.DataFrame with the (x, y) of all the players in the frame
            ball_coordinates : position (x,y) of the ball
            time : str giving the time
        """
        # Take the tracking data that is available for the frame
        frame_coordinates = self.df_tracking.loc[frame_id]["data"]

        # Ball
        ball_coordinates = next(
            (
                position
                for position in frame_coordinates
                if position.get("trackable_object") == self.id_ball
            ),
            None,
        )

        # Players
        player_coordinates = [
            item
            for item in frame_coordinates
            if (
                item.get("trackable_object") != self.id_ball
                and item.get("trackable_object") is not None
                and item.get("trackable_object") not in self.id_referee
                and item.get("group_name") != "referee"
            )
        ]
        df_player_coordinates = pd.DataFrame(player_coordinates)
        # Get information regarding the team and the jersey colors
        if len(player_coordinates) > 0:
            df_player_coordinates = df_player_coordinates.merge(
                self.df_players, how="left"
            )
            df_player_coordinates["team_id"] = df_player_coordinates.apply(
                lambda x: self.teams.get(x["group_name"].replace(" ", "_"))["team_id"]
                if pd.isna(x["team_id"])
                else x["team_id"],
                axis=1,
            )
            df_player_coordinates = df_player_coordinates.merge(
                self.df_teams[["team", "short_name", "team_id", "jersey_color"]]
            )

        time = self.df_tracking.loc[frame_id].time
        return df_player_coordinates, ball_coordinates, time

    def plot_frame(self, frame_id: int, trajectories_from:int=None):
        """
        Plot a pitch with what it is visible on the frame

        Args:
            frame_id (int): identifier of a frame
            trajectories_from (int) : number of frames to take to draw the trajectories before the frame_id
        """
        # Get the coordinates from the frame
        df_player_coordinates, ball_coordinates, time = self.get_coordinates_from_frame(
            frame_id
        )

        # Draw the pitch
        fig, ax = plot_pitch()

        # If the frame is empty
        if len(df_player_coordinates) == 0:
            print("The frame is empty")
            return None, None

        # Plot the ball if visible
        if ball_coordinates is not None:
            x_ball, y_ball = ball_coordinates["x"], ball_coordinates["y"]
            ax.plot(x_ball, y_ball, marker="D", markersize=17, color="k", alpha=0.2)

        # Plot the home and away players'positions
        home_team = df_player_coordinates[df_player_coordinates["team"] == "home_team"]
        away_team = df_player_coordinates[df_player_coordinates["team"] == "away_team"]

        if len(home_team) > 0:
            home_color = home_team["jersey_color"].unique()[0]
            home_team_name = home_team["short_name"].unique()[0]
        else:
            home_color = 'black'
            home_team_name = ''
        if len(away_team) > 0:
            away_color = away_team["jersey_color"].unique()[0]
            away_team_name = away_team["short_name"].unique()[0]
        else:
            away_color = 'black'
            away_team_name = ''

        ax.plot(home_team["x"], home_team["y"], "o", color=home_color, markersize=10)
        ax.plot(away_team["x"], away_team["y"], "o", color=away_color, markersize=10)

        # Get a legend-title with the color of the teams
        home_title_x = -len(home_team_name) * 2.5
        away_title_x = 5
        if home_color == "#ffffff":
            home_color = "black"
        if away_color == "#ffffff":
            away_color = "black"

        ax.text(
            home_title_x,
            40,
            home_team_name,
            fontsize=18,
            color=home_color,
            weight="black",
        )
        ax.text(0.5, 40, " - ", fontsize=18, color="black", ha="center", weight="black")
        ax.text(
            away_title_x,
            40,
            away_team_name,
            fontsize=18,
            color=away_color,
            weight="black",
        )

        # Plot the time to have a clock displayed
        ax.text(-55, 45, frame_id, fontsize=14, color="black", weight="black")
        ax.text(-55, 40, time, fontsize=14, color="black", weight="black")

        if trajectories_from is not None:
            # Get the data for the chosen interval
            df_tracking_interval = self.df_tracking[["data", "frame"]].explode("data"
                                                    ).loc[(frame_id-trajectories_from):frame_id]
            df_tracking_interval = pd.concat([
                df_tracking_interval.apply(extract_values, axis=1), 
                df_tracking_interval[["frame"]]], axis=1)
            
            # Get the list of coordinates by object
            df_tracking_interval = df_tracking_interval[
                ["trackable_object", "x", "y"]].groupby("trackable_object").agg(list)
            
            # Get the information about the color
            df_tracking_interval = df_tracking_interval.reset_index().merge(
                                        self.df_players, how="left").merge(
                                        self.df_teams, how='left')[
                                            ["trackable_object", "x", "y", "jersey_color"]]
            df_tracking_interval["jersey_color"] = df_tracking_interval["jersey_color"].fillna("grey")
            for _, row in df_tracking_interval.iterrows():
                ax.plot(row["x"], row["y"], color=row["jersey_color"], linewidth=2, linestyle="dotted")

        return fig, ax


    def draw_gif_actions(self, frame_start: int):
        """
        Draw and save a gif animtation of the action

        Args:
            frame_start (int): frame from the beginnon
        """
        count = 0
        images = []

        home = self.match_data["home_team"]["acronym"]
        away = self.match_data["away_team"]["acronym"]

        # First check if the gif has not yet drawn done, otherwise load the gif
        if os.path.exists(f"gif/{home}-{away}_{frame_start}.gif"):
            print(f"{self.match_id} : gif exists")

        else:
            # Create the images every two frames
            for frame in tqdm(range(frame_start, frame_start + 200, 2)):
                # If the frame is empty
                if len(self.get_coordinates_from_frame(frame)[0]) > 0:
                    count += 1
                    fig, ax = self.plot_frame(frame)
                    plt.savefig(f"img/{count}.png")
                    images.append(f"img/{count}.png")
                    plt.close()

            # Save the gif
            with imageio.get_writer(
                f"gif/{home}-{away}_{frame_start}.gif", mode="I"
            ) as writer:
                for filename in images:
                    image = imageio.imread(filename)
                    writer.append_data(image)

        display(Image(filename=f"gif/{home}-{away}_{frame_start}.gif"))
