class Led():
    _layer : int
    color : tuple

    # Constructor
    def __init__(self, layer, color):
        self._layer = layer
        self.color = color
    
    @property
    def layer(self):
        return self._layer

    @layer.setter
    def layer(self, value):
        if value < -1:
            self._layer = -1
        else:
            self._layer = value