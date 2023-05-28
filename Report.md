
# Report Corner Kicks Analysis Project

> Author : Chloe Gobe [[Github]](https://github.com/ChloeGobe/corner-kicks-analysis) [[Linkedin]](https://www.linkedin.com/in/chloe-gobe/)

> Date: May 28th 2023


## Summary :

1. [Handling the data](#data)
2. [Identification of the corner kicks situations](#identification)
3. [Opposition Analysis](#opposition)

## 1. Handling the data<a id="data"></a>

To help me manipulate SkillCorner's data more easily, I started by creating a `Match` class. This class allows to transform the data into more usable elements, collect the desired information, and most importantly, visualize and represent different actions since match replays are not available.

The methods can be found in the file `match_toolbox.py`

## 2. Identification of corner kicks situations<a id="identification"></a>

### 2.a. Method

While the definition of a corner kick is simple in the rules of football, it is more challenging to define it solely based on televised tracking data.

The available data for frames depends on the camera's captured image and the ability of SkillCorner's models to detect players and the ball within a compact group of players, for example.

I started by reviewing match reports on the Internet to find out the number of corners awarded in each match. I also obtained summarized videos to identify different corners and compare the broadcast with the tracking data to determine various scenarios.

I implemented three types of tests:

A. **Ball position in the corner:**
  - If the ball is detected in a corner $c_{k}$ of the field
$$\bigcup_{c_{k}}\ (x_{ball} - x_{c_{k}})^2 + (y_{ball} - y_{c_{k}})^2 \leq 1\quad(i)$$

  - And if its z-position is less than 20 cm to avoid detecting throw-ins

$$z_{ball} < 0.2\ m\quad(ii)$$
  
To be more precise about the timestamp of a starting corner kick, a linear interpolation of the ball position was performed using 60 frames around the analyzed frame.


B. **Player position in the corner:**
  - If a player $p_{i}$ is detected in a corner $c_{k}$ of the field [^1]

$$\bigcup_{c_{k}}\bigcup_{p_{i}}\ (x_{p_{i}} - x_{c_{k}})^2 + (y_{p_{i}} - y_{c_{k}})^2 \leq 1\quad(iii)$$

C. **Ensuring that two opponents are not within a distance less than 10 yards from the corner** 

- According to the rule, during a corner kick, the defending team cannot approach the ball within this distance. Having two opposing players in this zone would invalidate the assumption that it is a corner kick situation. If no players are visible in this area, the assumption of a corner remains valid if the camera is focusing on the players in the penalty area.

Therefore, the method used is to annotate the frames based on their potential to represent the start of a corner situation:
$$(A \lor B)\land C$$

Then, the beginning of the corner is detected if it is the first frame within 1 second to be identified as a candidate.

This way, we have a list of potential first frames of corner situations.

### 2.b. Results

The method allows for the detection of a reasonable number of corners, close to the count provided by match summaries. There are few false positives but some corner kicks are missing.

### 2.c. Discussion

#### Pros

- The proposed method allows for quickly finding a list of potential corner situations, along with their starting frames, without relying on machine learning. 
- The criteria used are straightforward from a football perspective. 
- Visualizing these situations with the previously developed methods helps determine if they are false positives.

#### Cons

- The algorithm takes a considerable amount of time to perform this task (approximately 7 to 8 minutes per match and up to 35mn with the linear interpolation).
- There is a significant number of corner kicks missing
- Several specific situations remain challenging to handle.

#### With more time and/or data

Here are some potential areas of improvement:

- Focus only on players in the corner who are in the opponent's half (all players were considered in this case for simplicity, assuming that the situation where a defender is in their own corner without any opponents around is rare).

- Trying to fill the gap in the position data by interpolate the x and y coordinates of all trackable objects through all the frames. 

- Data providers like WyScout and Statsbomb offer event data, where events are annotated by humans. By combining such data with a larger quantity of broadcast tracking data, it would be possible to create a supervised machine learning model that takes into account many more parameters: the number of players in the penalty area, sum of the transverse component of players during the corner, direction of the ball towards the penalty area, ball going out of play, previous possession, etc. This would provide a probability of being a corner situation.

## 3. Opposition Analysis<a id="opposition"></a>

### 3.a. Method

Two elements can be analyzed :

- the number of defenders and attackers within the box during the corner kick
- the movement of each player during the corner kick

### 3.b. Results

The analysis has been performed on two corner kicks from the Livepool - Manchester City game and can be found in the Jupyter Notebook

#### With more time and/or data

- Other metrics could have been computed :
	- the delivery zone of the ball
	- the delivery type (inswing)
	- if there is a shot on first touch or a pass on first touch
	- if the defenders are using a man-to-man, zonal or hybrid system
	
- Using more games to get more precise information about the corner kicks playbooks of the opponents

- Given more data, expertise and labelled data, it could be possible to reproduce the research of L. Shaw and S. Gopaladesikan [^2]. Using machine learning, it will be possible to analyse how the opponent attacks and therefore prepare the defense to be efficient, and how they defende to try to find a successul way to score a goal.
 

-------

[^1] : _Automatic event detection in football using tracking data_ Vidal-Codina, Ferran & Evans, Nicolas & Fakir, Bahaeddine & Billingham, Johsan. (2022) Sports Engineering. 25. 10.1007/s12283-022-00381-6. 

[^2] : _Routine Inspection: A playbook for corner kicks_, Laurie Shaw, Sudarshan Gopaladesikan (Sloan Sports Analytics Conference, 2020) [pdf]
