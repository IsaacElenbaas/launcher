An expandable application launcher written Python with minimal dependencies. There are curved edges and the skeleton of a theming system, but I do not have the time to contribute to this too much right now and have not decided on how to handle user settings.

[Demo](https://drive.google.com/file/d/1FVgHfEgsbgTacuC8t4PHa7BuQTJhr8mr/preview) (moving background is to showcase the transparency support **without a compositor**, typing sounds are from [osu-keysounds](https://github.com/IsaacElenbaas/osu-keysounds))

Dependencies:
```
python-cairocffi
python-pyxdg
python-xcffib
xsel for copying from calc
```
Currently only works on herbstluftwm, as there is no standard X way to determine the focused monitor (that I can find), but that can be fixed by hardcoding offsets by the herbstclient call.
