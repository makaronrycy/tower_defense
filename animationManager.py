from PySide6.QtGui import QPixmap, QImage, QPainter, QTransform
import json
from PySide6.QtCore import QRect, Qt, QSize
class SpriteSheet:
    def __init__(self, filename):
        self.sheet = QPixmap(filename)
    def get_frame(self, rect):
        """Get specific frame from sheet"""
        return self.sheet.copy(rect)




class AnimationComponent:
    def __init__(self, spritesheet :SpriteSheet, animations):
        """
        structure:
            {
                "idle":{
                    "from": 0
                    "to" : 4
                    0 :{
                        "rect": QRect(x,y,w,h)
                        "duration" = 0.1
                    }
                    1 :{
                        "rect": QRect(x,y,w,h)
                        "duration" = 0.1
                    }
                    2 :{
                        "rect": QRect(x,y,w,h)
                        "duration" = 0.1
                    }
                }
                "attack":{
                    "from": 5
                    "to" : 6
                    5 :{
                        "rect": QRect(x,y,w,h)
                        "duration" = 0.1
                    }
                    6 :{
                        "rect": QRect(x,y,w,h)
                        "duration" = 0.1
                    }
                }                     
            }
        """
        self.spritesheet = spritesheet
        self.animations = animations
        self.current_anim = list(animations.values())[0]
        self.current_frame = 0
        self.current_time = 0.0

    def set_animation(self, name):
        if name in self.animations:
            self.current_anim = self.animations[name]
            self.current_frame = 0
            self.current_time = 0.0
        else:
            raise ValueError(f"Animation '{name}' not found.")
    def get_current_frame(self):
        if self.current_frame in self.current_anim:
            frame_data = self.current_anim[self.current_frame]
            return self.spritesheet.get_frame(frame_data["rect"])
        else:
            raise ValueError(f"Frame '{self.current_frame}' not found in current animation.")
    def get_current_pixmap(self):
        """Get the current frame as a QPixmap"""
        if not self.current_anim or self.current_frame not in self.current_anim:
            # Return a placeholder or empty pixmap if no valid frame
            return QPixmap()
            
        frame_data = self.current_anim[self.current_frame]
        # Cache the frame if needed for performance
        return self.spritesheet.get_frame(frame_data["rect"])
    def update(self, delta_time):
        """Update animation based on elapsed time in seconds"""
        if not self.current_anim or len(self.current_anim) == 0:
            return  # Skip if no animation data
            
        self.current_time += delta_time
        
        # Get the current frame duration in seconds
        current_duration = self.current_anim[self.current_frame]["duration"] / 1000.0
        
        if self.current_time >= current_duration:
            # Subtract the used time instead of resetting to 0
            self.current_time -= current_duration
            self.current_frame = (self.current_frame + 1) % len(self.current_anim)


class AsepriteLoader:
    def __init__(self, json_file):
        with open(json_file) as f:
            self.data = json.load(f)
            
    def get_tileset_data(self):
        """
        structure:
            {
                "tileset_name": QRect(x,y,w,h)
            }
        """
        tileset_data = {}
        for slice in self.data["meta"]["slices"]:
            tile_bounds = slice["keys"][0]["bounds"]
            tileset_data[slice["name"]] = QRect(tile_bounds["x"], tile_bounds["y"], tile_bounds["w"], tile_bounds["h"])
        print(tileset_data)
        return tileset_data
    def get_anim_data(self):
        
        animation_data = {}
        frames = list(self.data["frames"].values())
        for tags in self.data["meta"]["frameTags"]:
            animation_data[tags["name"]] = {}
            start = tags["from"]
            end = tags["to"]
            duration = end - start +1
            for i in range(0,duration):     
                animation_data[tags["name"]][i] = {}   
                animation_data[tags["name"]][i]["rect"] = QRect(frames[i+start]["frame"]["x"],frames[i+start]["frame"]["y"],frames[i+start]["frame"]["w"],frames[i+start]["frame"]["h"],)
                animation_data[tags["name"]][i]["duration"] = (frames[i+start]["duration"]) #in ms
            print(animation_data)
        return animation_data

def get_all_animations():
    bomb_tower_animation = AsepriteLoader("spritesheets/bomb_tower.json")
    bomb_tower_spritesheet = SpriteSheet("spritesheets/bomb_tower.png")
    bomb_tower_spritesheet_1 = SpriteSheet("spritesheets/bomb_tower_1.png")
    bomb_tower_spritesheet_2 = SpriteSheet("spritesheets/bomb_tower_2.png")

    basic_tower_animation = AsepriteLoader("spritesheets/basic_tower.json")
    basic_tower_spritesheet = SpriteSheet("spritesheets/basic_tower.png")
    basic_tower_spritesheet_1 = SpriteSheet("spritesheets/basic_tower_1.png")
    basic_tower_spritesheet_2 = SpriteSheet("spritesheets/basic_tower_2.png")
    basic_tower_spritesheet_3 = SpriteSheet("spritesheets/basic_tower_3.png")

    booster_tower_animation = AsepriteLoader("spritesheets/booster_tower.json")
    booster_tower_spritesheet = SpriteSheet("spritesheets/booster_tower.png")

    booster_tower_spritesheet_1 = SpriteSheet("spritesheets/booster_tower_1.png")
    booster_tower_spritesheet_2 = SpriteSheet("spritesheets/booster_tower_2.png")
    booster_tower_spritesheet_3 = SpriteSheet("spritesheets/booster_tower_3.png")

    rat_animation = AsepriteLoader("spritesheets/rat.json")
    rat_spritesheet = SpriteSheet("spritesheets/rat.png")
    fast_rat_animation = AsepriteLoader("spritesheets/fast_rat.json")
    fast_rat_spritesheet = SpriteSheet("spritesheets/fast_rat.png")
    giant_rat_animation = AsepriteLoader("spritesheets/giant_rat.json")
    giant_rat_spritesheet = SpriteSheet("spritesheets/giant_rat.png")
    basic_projectile_animation = AsepriteLoader("spritesheets/basic_projectile.json")
    basic_projectile_spritesheet = SpriteSheet("spritesheets/basic_projectile.png")
    bomb_projectile_animation = AsepriteLoader("spritesheets/bomb_projectile.json")
    bomb_projectile_spritesheet = SpriteSheet("spritesheets/bomb_projectile.png")
    explosion_projectile_animation = AsepriteLoader("spritesheets/explosion_projectile.json")
    explosion_projectile_spritesheet = SpriteSheet("spritesheets/explosion_projectile.png")

    animations = {
        "bomb_tower":{
            "spritesheet" :bomb_tower_spritesheet,
            "upgrade1": bomb_tower_spritesheet_1,
            "upgrade2": bomb_tower_spritesheet_2,
            "anim_data": bomb_tower_animation.get_anim_data()
        }
        ,"basic_tower":{
            "spritesheet" :basic_tower_spritesheet,
            "upgrade1": basic_tower_spritesheet_1,
            "upgrade2": basic_tower_spritesheet_2,
            "upgrade3": basic_tower_spritesheet_3,
            "anim_data": basic_tower_animation.get_anim_data()
        }
        ,"booster_tower":{
            "spritesheet" :booster_tower_spritesheet,
            "upgrade1": booster_tower_spritesheet_1,
            "upgrade2": booster_tower_spritesheet_2,
            "upgrade3": booster_tower_spritesheet_3,
            "anim_data": booster_tower_animation.get_anim_data()
        }
        ,"rat":{
            "spritesheet" :rat_spritesheet,
            "anim_data": rat_animation.get_anim_data()
        }
        ,"fast_rat":{
            "spritesheet" :fast_rat_spritesheet,
            "anim_data": fast_rat_animation.get_anim_data()
        }
        ,"giant_rat":{
            "spritesheet" :giant_rat_spritesheet,
            "anim_data": giant_rat_animation.get_anim_data()
        }
        ,"basic_projectile":{
            "spritesheet" :basic_projectile_spritesheet,
            "anim_data": basic_projectile_animation.get_anim_data()
        }
        ,"bomb_projectile":{
            "spritesheet" :bomb_projectile_spritesheet,
            "anim_data": bomb_projectile_animation.get_anim_data()
        }
        ,"explosion_projectile":{
            "spritesheet" :explosion_projectile_spritesheet,
            "anim_data": explosion_projectile_animation.get_anim_data()
        }
    }
    return animations




