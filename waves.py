from graphicItems import Rat, GiantRat, FastRat
tower_defense_waves = {
    1: {
        "name": "Wave 1",
        "enemies": [
            {"type": Rat, "count": 5, "delay": 0},
        ],
        "delay": 0,
        "duration": 20,
    },
    2: {
        "name": "Wave 2",
        "enemies": [
            {"type": Rat, "count": 5, "delay": 0},
            {"type": FastRat, "count": 3, "delay": 5},
        ],
        "delay": 0,
        "duration": 20,
    },
    3: {
        "name": "Wave 3",
        "enemies": [
            {"type": Rat, "count": 5, "delay": 0},
            {"type": GiantRat, "count": 3, "delay": 5},
            {"type": FastRat, "count": 2, "delay": 10},
        ],
        "duration": 20,
    },
    4: {
        "name": "Wave 4",
        "enemies": [
            {"type": Rat, "count": 5, "delay": 0},
            {"type": GiantRat, "count": 3, "delay": 5},
            {"type": FastRat, "count": 2, "delay": 10},
        ],
        "duration": 20,
    },
    5: {
        "name": "Wave 5",
        "enemies": [
            {"type": Rat, "count": 5, "delay": 0},
            {"type": GiantRat, "count": 3, "delay": 5},
            {"type": FastRat, "count": 2, "delay": 10},
        ],
        "duration": 20,
    },
}