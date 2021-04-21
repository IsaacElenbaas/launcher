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

`calc` can also be called from the command line; below is an example and its output.
```
./calc.py "x=12+4%3;2x^floor(dist([7,2],[3,4])/3)"
Input: x=12+4%3;2x^floor(dist([7,2],[3,4])/3)
Solving (top level): x=12+4%3
Solving basic math: 12+4%3
[4.0, '%', 3.0]
[12.0, '+', 1.0]
Solving (top level): 2*x^floor(dist([7,2],[3,4])/3)
Solving basic math: [7,2],[3,4]
Working on section: dist([7,2],[3,4])/3
['dist([7,2],[3,4])']
Solving basic math: 4.47213595499957961010/3
[4.47213595499958, '/', 3.0]
Working on section: 2*x^floor(1.49071198499985979602)
['floor(1.49071198499985979602)']
['x']
After expanding vars: 2*13^1
Solving basic math: 2*13^1
[13.0, '^', 1.0]
[2.0, '*', 13.0]
26
```
