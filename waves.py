import random
ENEMY_LIST = [{
        "rat" : 5
    },
    {
        "rat" : 10,
        "fast_rat" : 5

    },
    {
        "rat" : 10,
        "fast_rat" : 5,
        "giant_rat" : 2
    },
    {
        "rat" : 10,
        "fast_rat" : 5,
        "giant_rat" : 4
    },
    {
        "rat" : 10,
        "fast_rat" : 5,
        "giant_rat" : 6
    },]

def build_new_wave(current_wave,):
    scaling_factor = 1 + (current_wave // 5) * 0.1
    enemies_in_wave = {
        "rat" : int(ENEMY_LIST[5]["rat"] * scaling_factor),
        "fast_rat" : int(ENEMY_LIST[5]["fast_rat"] * scaling_factor),
        "giant_rat" : int(ENEMY_LIST[5]["giant_rat"] * scaling_factor)
    }
    enemies_in_wave["rat"] += random.randint(0, int(3*scaling_factor))
    enemies_in_wave["fast_rat"] += random.randint(0, int(3*scaling_factor))
    enemies_in_wave["giant_rat"] += random.randint(0, int(3*scaling_factor))
    surge_chance = random.random()
    if surge_chance > 0.7:
        enemy_type = random.choice(["rat", "fast_rat", "giant_rat"])
        surge_amount = int(random.randint(3, 8) * scaling_factor)
        print(f"Wave {current_wave}: Surge of {surge_amount} {enemy_type}s!")
        enemies_in_wave[enemy_type] += surge_amount
        
    # Increment wave number for next time
    random.shuffle(enemies_in_wave)
    current_wave += 1
    return enemies_in_wave

        

        
        