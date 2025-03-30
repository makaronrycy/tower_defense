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
            
        self.spritesheet = QPixmap(self.data['meta']['image'])

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



