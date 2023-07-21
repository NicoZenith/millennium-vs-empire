import json 
import sqlite3
import os 



def get_all_paths_with_sequential_time(database_path, origin, destination):
    """
    Reads through the SQLite database ROUTE and outputs all the possible paths from Tatooine to Endor
    :database_path: where the database is stored 
    :origin: the planet the ship starts from (Tatooine)
    :destination: the planet the ship aims (Endor)

    :return: all paths (stops between Tatooine and Endor) along with their travel times
    """
    # Establish a connection to the SQLite database
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()

    def find_paths(current_node, current_time=0, path=[]):
        # Add the current node and its time to the path
        path = path + [(current_node, current_time)]
        if current_node == destination:
            # If the current node is the destination, yield the path excluding the first element (start node and initial time 0)
            yield path[1:]
        else:
            # Execute a SELECT query to find all neighbors of the current node and their travel times (both forward and backward)
            cursor.execute("SELECT destination, travel_time FROM ROUTES WHERE origin=?", (current_node,))
            forward_rows = cursor.fetchall()
            cursor.execute("SELECT origin, travel_time FROM ROUTES WHERE destination=?", (current_node,))
            backward_rows = cursor.fetchall()

            for row in forward_rows:
                next_node, travel_time = row
                if next_node not in [node for node, _ in path]:  # Avoid cycles by checking if the next node is already in the path
                    # Recursively call find_paths for each forward neighbor node with updated current time
                    yield from find_paths(next_node, travel_time, path)

            for row in backward_rows:
                prev_node, travel_time = row
                if prev_node not in [node for node, _ in path]:  # Avoid cycles by checking if the previous node is already in the path
                    # Recursively call find_paths for each backward neighbor node with updated current time
                    yield from find_paths(prev_node, travel_time, path)

    # Find all paths from the origin to the destination
    all_paths = list(find_paths(origin))

    # Close the database connection
    conn.close()

    return all_paths



def compute_probability(count_bounty):
    """
    Computes the probability of getting captured on a given day
    :count_bounty: the number of times we encountered a bounty hunter 
    """
    return 9**(count_bounty)/10**(count_bounty+1)

def check_bounty(bounty_hunters, current_day, current_planet):
    """
    Checks is there is a bounty hunter on a given day and planet
    :bounty_hunters: stores the information about bounty hunters (day and planet)
    :current_day: the day we check if there is a bounty hunter 
    :current_planet: the planet we check if there is a bounty hunter 

    :return: if there is a bounty hunter or not (boolean)
    """
    return any(hunter['day'] == current_day and hunter['planet'] == current_planet for hunter in bounty_hunters)


def num_of_days_to_wait(base_autonomy, path_times, countdown):
    """
    Computes the number of days we can afford to wait on the whole trip
    :base_autonomy: base autonomy of the falcon 
    :path_times: stores the travel times between each planet of the given path 
    :countdown: the number of days before the death star kills 

    :return: the number of days we can afford to wait given the countdown and the path 
    """
    autonomy = base_autonomy
    total_time = 0
    for j in range(len(path_times)):
        if autonomy >= path_times[j]:
            autonomy -= path_times[j]
            total_time += path_times[j]
        else:
            total_time += 1 
            autonomy = base_autonomy - path_times[j]
            total_time += path_times[j]
    return max(countdown - total_time, 0)





def compute_probas_per_path(all_paths_stops, all_paths_times, base_autonomy, countdown, bounty_hunters, origin_station):
    """
    Computes the probability of success of each path going from Tatooine to Endor  
    This probability is discounted everytime the ship is on the same planet as a bounty hunter 
    The ship is allowed to wait if it has enough time 
    :all_paths_stops: list containing each path (= list that contains each stop until Endor)
    :all_paths_times: list containing each path (= list that contains each travel time until Endor)
    :base_autonomy: the base autonomy the Falcon has and can refuel to 
    :countdown: number of days before the Death Star kills 
    :bounty_hunters: informations about the bounty hunters 
    :origin_station: where the ship starts from (Tatooine)

    :return: list containing probabilities of success for all paths
    """

    all_paths_probabilities = []

    # We loop over the possible paths computed above
    for i in range(len(all_paths_stops)):
        total_time = 0 # initialize the travel time to 0 
        probability = 1 # we will discount from the maximal probability, 1 
        autonomy = base_autonomy # initialize the autonomy of the falcon to its base 
        count_bounty = 0 # tracks the number of times we encountered a bounty hunter 

        # Compute the number of days we are allowed to wait on a planet to avoid bounty hunters 
        num_wait = num_of_days_to_wait(base_autonomy, all_paths_times[i], countdown) 

        for j in range(len(all_paths_stops[i])):
            current_planet = all_paths_stops[i][j-1] if j > 0 else origin_station # the current planet we are in the path 
            planet_to_travel_to = all_paths_stops[i][j] # check the next stop of the path 
            time_to_planet = all_paths_times[i][j] # check the time it takes to get there 

            # Check if we have enough fuel to go to the next planet 
            if autonomy >= time_to_planet:
                autonomy -= time_to_planet # in that case we lose autonomy 
                total_time += time_to_planet # and the total time increases by the travel time to the planet 

                # We check if there is a bounty hunter on the next planet. If we can afford to stay on the current planet while there is a bounty hunter on the next planet, we do it
                while check_bounty(bounty_hunters, total_time, planet_to_travel_to) and num_wait > 0:
                    total_time += 1 # if we wait, the total time increases by one day 
                    num_wait -= 1 # and we lose one day to wait 

                # After (possibly) waiting, we check if there is a bounty hunter on the next planet 
                if check_bounty(bounty_hunters, total_time, planet_to_travel_to):
                    probability -= compute_probability(count_bounty) # we discount the probability using the formula
                    count_bounty += 1 # we increase the times we encountered a bounty hunter 
                
                
            # if we don't have enough fuel, we need to refuel 
            else:
                total_time += 1 # refueling takes one day 
                autonomy = base_autonomy # we reset the autonomy to its base 
                
                # if a bounty hunter is here, we discount the probability of success 
                if  check_bounty(bounty_hunters, total_time, current_planet):
                    probability -= compute_probability(count_bounty)
                    count_bounty+=1
                
                # once refueled, we go to the next planet 
                total_time += time_to_planet
                autonomy -= time_to_planet

                # however we can check if there is a bounty hunter on the next planet, and wait if we can afford it (and if there is no bounty hunter on the current planet) 
                while check_bounty(bounty_hunters, total_time, planet_to_travel_to) and not check_bounty(bounty_hunters, total_time, current_planet) and num_wait > 0:
                    total_time += 1
                    num_wait -= 1
                # if there is a bounty hunter on the next planet, we discount the probability 
                if check_bounty(bounty_hunters, total_time, all_paths_stops[i][j]) :
                    probability -= compute_probability(count_bounty)
                    count_bounty += 1

        # if the falcon takes more time than the countdown, probability of success is 0 
        if total_time > countdown:
            probability = 0

        # add the probability of the path 
        all_paths_probabilities.append(probability)

    return all_paths_probabilities


def calculate_odds(millennium_file, empire_file):
    """
    Reads the millennium and empire files and output the maximal probability of success for the ship arriving to Endor 
    :millennium_file: contains information about the origin station, the destination station and the routes it can take 
    :empire_file: contains information about the countdown, and the planet and time the bounty hunters are 

    :return: maximal probability of success (the aim of the project)
    """
    with open(millennium_file) as millennium:
        data_millennium = json.load(millennium)

    with open(empire_file) as empire:
        data_empire = json.load(empire)

    base_autonomy = data_millennium["autonomy"]
    countdown = data_empire["countdown"]
    bounty_hunters = data_empire["bounty_hunters"]

    origin_station = data_millennium["departure"]
    destination_station = data_millennium["arrival"]
    universe_file = data_millennium["routes_db"]  # Use data_millennium["routes_db"] as the path to the SQLite database file

    # Get the directory path of "millennium-falcon.json"
    directory_path = os.path.dirname(os.path.abspath(millennium_file))
    # Construct the path to "universe.db" in the same directory as "millennium-falcon.json"
    universe_file = os.path.join(directory_path, "universe.db")

    # Fetch all paths from the origin to the destination using the backend function
    paths = get_all_paths_with_sequential_time(universe_file, origin_station, destination_station)

    all_paths_stops = []  # stores all the paths (planets)
    all_paths_times = []  # stores all the paths (travel times)

    # Store all the paths by planet and by time
    for path in paths:
        stops, travel_times = zip(*path)
        stops = [stop for stop in stops]
        all_paths_stops.append(stops)
        travel_times = [time for time in travel_times]
        all_paths_times.append(travel_times)

    # Load data from the configuration file (universe database, origin, and destination)
    # Compute probabilities using compute_probas_per_path backend function
    all_paths_probabilities = compute_probas_per_path(
        all_paths_stops, all_paths_times, base_autonomy, countdown, bounty_hunters, origin_station
    )

    # Calculate maximum probability from all_paths_probabilities list
    max_probability = max(all_paths_probabilities)


    return max_probability*100