from game_objects.animationManager import AsepriteLoader,SpriteSheet

def get_tileset():
    tileset_data = AsepriteLoader("spritesheets/tileset-sheet.json").get_tileset_data()
    spritesheet = SpriteSheet("spritesheets/tileset.png")
    tileset = {}
    for key, value in tileset_data.items():
        tileset[key] = spritesheet.get_frame(tileset_data[key])
    return tileset
        
        