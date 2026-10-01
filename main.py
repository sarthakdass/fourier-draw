"""
Fourier series drawing visualizer.

Draw a closed path with the mouse, press SPACE, and the path is decomposed into
201 rotating vectors (harmonics n = -100 .. 100) that are added tip to tail.
The tip of the final vector retraces the drawing.

Math
----
The drawing is treated as a complex-valued function f(t), t in [0, 1], where a
screen point (x, y) becomes the complex number x + iy (measured from the centre
of the window).  The approximation is

    f(t) ~ sum_{n=-N}^{N} c_n * exp(2*pi*i*n*t)

    c_n = integral_0^1 f(t) * exp(-2*pi*i*n*t) dt

The integral is evaluated numerically from the resampled path:

    c_n ~ (1/K) * sum_{k=0}^{K-1} f(k/K) * exp(-2*pi*i*n*k/K)

Each term c_n * exp(2*pi*i*n*t) is a vector of length |c_n| starting at angle
arg(c_n) and spinning n times per cycle (negative n spins clockwise).

Controls
--------
  mouse drag      draw a path
  SPACE           finish drawing / start over
  LEFT / RIGHT    use fewer / more terms
  UP / DOWN       speed up / slow down
  G               toggle the faint original drawing
  ESC             quit
"""

import asyncio
import cmath
import math

import pygame

# --- configuration ----------------------------------------------------------

WIDTH, HEIGHT = 1100, 760
FPS = 60

HARMONICS = 100          # n runs from -HARMONICS to +HARMONICS -> 201 vectors
SAMPLES = 1500           # points used to approximate the integral for c_n
CYCLE_SECONDS = 12.0     # seconds for t to go from 0 to 1
MIN_CIRCLE_RADIUS = 1.5  # circles smaller than this are not drawn

BG = (14, 16, 22)
GUIDE = (58, 64, 80)
CIRCLE = (52, 58, 74)
VECTOR = (142, 152, 172)
TRACE = (118, 220, 255)
INK = (232, 236, 244)
LABEL = (138, 148, 168)

CENTER = complex(WIDTH / 2, HEIGHT / 2)


# --- geometry ---------------------------------------------------------------


def to_screen(z):
    """Complex number (relative to the window centre) -> pixel coordinates."""
    return (z.real + CENTER.real, z.imag + CENTER.imag)


def resample_closed(points, count):
    """Walk the path at constant speed and return `count` evenly spaced points.

    The path is closed first (last point joined back to the first) so that f(t)
    is genuinely periodic, which is what the Fourier series assumes.  Spacing by
    arc length rather than by mouse sample means a slow, careful corner does not
    soak up a disproportionate chunk of t.
    """
    path = list(points)
    if path[0] != path[-1]:
        path.append(path[0])

    cumulative = [0.0]
    for a, b in zip(path, path[1:]):
        cumulative.append(cumulative[-1] + abs(b - a))
    total = cumulative[-1]
    if total == 0:
        return [path[0]] * count

    out = []
    j = 0
    for i in range(count):
        target = total * i / count
        while j < len(path) - 2 and cumulative[j + 1] < target:
            j += 1
        span = cumulative[j + 1] - cumulative[j]
        frac = 0.0 if span == 0 else (target - cumulative[j]) / span
        out.append(path[j] + (path[j + 1] - path[j]) * frac)
    return out


# --- the Fourier part -------------------------------------------------------


def fourier_coefficients(samples, harmonics):
    """Return [(n, c_n), ...] for n = -harmonics .. harmonics."""
    k = len(samples)
    coefficients = []
    for n in range(-harmonics, harmonics + 1):
        total = 0j
        exponent = -2j * math.pi * n / k
        for index, value in enumerate(samples):
            total += value * cmath.exp(exponent * index)
        coefficients.append((n, total / k))
    return coefficients


def order_by_size(coefficients):
    """Largest circles first: nicer to watch, and truncating keeps the best terms."""
    return sorted(coefficients, key=lambda item: abs(item[1]), reverse=True)


def epicycle_positions(terms, t):
    """Add the vectors tip to tail, returning every joint from origin to tip."""
    position = 0j
    joints = [position]
    for n, c in terms:
        position += c * cmath.exp(2j * math.pi * n * t)
        joints.append(position)
    return joints


# --- rendering --------------------------------------------------------------


def load_font(size):
    for name in ("consolas", "menlo", "dejavusansmono", "couriernew"):
        if name in pygame.font.get_fonts():
            return pygame.font.SysFont(name, size)
    return pygame.font.Font(None, size + 4)


def draw_text(screen, font, lines, color=LABEL):
    for i, line in enumerate(lines):
        screen.blit(font.render(line, True, color), (18, 18 + i * 20))


def draw_epicycles(screen, joints):
    for start, end in zip(joints, joints[1:]):
        radius = abs(end - start)
        if radius >= MIN_CIRCLE_RADIUS:
            pygame.draw.circle(screen, CIRCLE, to_screen(start), int(radius), 1)
            pygame.draw.aaline(screen, VECTOR, to_screen(start), to_screen(end))


def draw_path(screen, points, color, width):
    if len(points) < 2:
        return
    pixels = [to_screen(z) for z in points]
    if width == 1:
        pygame.draw.aalines(screen, color, False, pixels)
    else:
        pygame.draw.lines(screen, color, False, pixels, width)


# --- main loop --------------------------------------------------------------


async def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Fourier Series Drawing")
    clock = pygame.time.Clock()
    font = load_font(16)

    mode = "draw"          # "draw" or "animate"
    raw = []               # the mouse path, complex, relative to the centre
    pen_down = False
    terms = []             # [(n, c_n)] ordered by |c_n|
    used = 0               # how many of those terms are currently drawn
    trail = []             # the curve traced by the final tip
    t = 0.0
    cycle = CYCLE_SECONDS
    show_guide = True

    def reset():
        nonlocal mode, raw, terms, used, trail, t, pen_down
        mode, raw, terms, used, trail, t, pen_down = "draw", [], [], 0, [], 0.0, False

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    if mode == "draw" and len(raw) >= 2:
                        draw_text(screen, font, ["computing coefficients..."], INK)
                        pygame.display.flip()
                        samples = resample_closed(raw, SAMPLES)
                        terms = order_by_size(fourier_coefficients(samples, HARMONICS))
                        used = len(terms)
                        trail, t, mode = [], 0.0, "animate"
                    else:
                        reset()
                elif event.key == pygame.K_g:
                    show_guide = not show_guide
                elif event.key == pygame.K_UP:
                    cycle = max(2.0, cycle - 1.0)
                elif event.key == pygame.K_DOWN:
                    cycle = min(40.0, cycle + 1.0)
                elif event.key in (pygame.K_LEFT, pygame.K_RIGHT) and terms:
                    step = -5 if event.key == pygame.K_LEFT else 5
                    used = max(1, min(len(terms), used + step))
                    trail = []

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if mode == "animate":
                    reset()
                pen_down = True
                raw.append(complex(*event.pos) - CENTER)

            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                pen_down = False

            elif event.type == pygame.MOUSEMOTION and pen_down:
                point = complex(*event.pos) - CENTER
                if not raw or abs(point - raw[-1]) > 1.5:
                    raw.append(point)

        screen.fill(BG)

        if mode == "draw":
            draw_path(screen, raw, INK, 2)
            draw_text(screen, font, [
                "hold the left mouse button to draw a path",
                "SPACE  decompose it into rotating vectors",
                f"points: {len(raw)}",
            ])
        else:
            t = (t + dt / cycle) % 1.0
            joints = epicycle_positions(terms[:used], t)

            if show_guide:
                draw_path(screen, raw + raw[:1], GUIDE, 1)
            draw_epicycles(screen, joints)

            trail.append(joints[-1])
            del trail[: max(0, len(trail) - int(FPS * cycle))]
            draw_path(screen, trail, TRACE, 2)

            draw_text(screen, font, [
                f"terms: {used} of {len(terms)}   "
                f"(n = -{HARMONICS}..{HARMONICS})",
                f"t = {t:5.3f}   cycle = {cycle:.0f}s",
                "SPACE redraw   LEFT/RIGHT terms   UP/DOWN speed   G guide",
            ])

        pygame.display.flip()
        await asyncio.sleep(0)  # keeps the loop friendly to a pygbag web build

    pygame.quit()


if __name__ == "__main__":
    asyncio.run(main())
