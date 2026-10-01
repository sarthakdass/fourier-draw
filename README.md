# Fourier Series Drawing

Draw a shape with the mouse and watch 201 rotating vectors redraw it.

Built with Python, Pygame, `math` and `cmath`.

Additionally attached HTML version for my personal website.

![demo](docs/demo.gif)

## Run it

```bash
pip install pygame-ce
python main.py
```

## Controls

| key | action |
| --- | --- |
| mouse drag | draw a path |
| `SPACE` | decompose the path / start over |
| `LEFT` `RIGHT` | use fewer / more terms |
| `UP` `DOWN` | speed up / slow down |
| `G` | toggle the faint original drawing |
| `ESC` | quit |

## How it works

A point on screen at `(x, y)` is read as the complex number `x + iy`, measured
from the centre of the window. The drawing therefore becomes a complex-valued
function `f(t)` with `t` running from 0 to 1 over one trip around the path.

`exp(2*pi*i*t)` is a unit vector making one counterclockwise turn as `t` goes
from 0 to 1. Multiplying by a complex constant `c` scales it to length `|c|` and
starts it at angle `arg(c)`; replacing `t` with `n*t` makes it turn `n` times per
cycle, clockwise when `n` is negative. Adding 201 of those tip to tail gives

```
f(t) ~ sum from n = -100 to 100 of c_n * exp(2*pi*i*n*t)
```

and the coefficients come from

```
c_n = integral from 0 to 1 of f(t) * exp(-2*pi*i*n*t) dt
```

which `fourier_coefficients` evaluates as a Riemann sum over 1500 samples of the
path:

```
c_n ~ (1/K) * sum from k = 0 to K-1 of f(k/K) * exp(-2*pi*i*n*k/K)
```

Two details that matter more than they look like they should:

- **Arc-length resampling.** Mouse samples bunch up wherever you drew slowly.
  `resample_closed` walks the path at constant speed instead, so `t` is spread
  evenly over the shape, and it joins the last point back to the first so `f` is
  actually periodic. Without that you get ringing at the seam.
- **Ordering by `|c_n|`.** The vectors are drawn largest first. It looks better,
  and it means truncating with `LEFT` keeps the terms that carry the shape, so
  you can watch the approximation coarsen one harmonic at a time.

On a square path the 201-term reconstruction lands within about 0.6 px of the
original.
