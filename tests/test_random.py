import numpy as np
from typing import * 
from primate import random
from primate.random import _engines, _engine_prefixes, _random_gen

def test_seeding():
  s1 = random.rademacher(250, seed = -1)
  s2 = random.rademacher(250, seed = -1)
  assert any(s1 != s2), "random device not working"
  for i in np.random.choice(range(1000), size=10):
    s1 = random.rademacher(250, seed = i)
    s2 = random.rademacher(250, seed = i)
    assert all(s1 == s2), "seeding doesnt work"

def test_rademacher():
  assert np.all([r in [-1.0, +1.0] for r in random.rademacher(100)]), "Basic rademacher test failed"
  for engine in _engine_prefixes:
    counts = np.array([np.sum(random.normal(100, engine=engine)) for _ in range(1500)])
    cum_counts = np.cumsum(counts) / np.arange(1, len(counts)+1)
    assert abs(cum_counts[-1]) <= 1.0, f"Rademacher random number generator biased more than 1% (for engine {engine})"

def test_normal():
  for engine in _engine_prefixes:
    counts = np.array([np.sum(random.normal(100, engine=engine)) for _ in range(1500)])
    cum_counts = np.cumsum(counts) / np.arange(1, len(counts)+1)
    assert abs(cum_counts[-1]) <= 1.0, f"Normal random number generator biased more than 1% (for engine {engine})"

def test_rademacher_simd():

  import timeit
  timeit.timeit(lambda: random.rademacher(5000, seed = 10), number=5000)


  out = np.empty(5000, dtype=np.float32) * np.nan
  timeit.timeit(lambda: _random_gen.rademacher_simd_sx(out, 1, 10), number=5000)
  




# def test_rayleigh():
#   for engine in _engine_prefixes:
#     averages = np.array([np.mean(random.rayleigh(100, engine=engine)) for _ in range(500)])
#     # assert np.allclose(sums, 1.0, atol = 1e-1), "Rayleigh vectors not normalized"
#     cum_avgs = np.cumsum(averages) / np.arange(1, len(averages)+1)
#     assert abs(cum_avgs[-1]) <= 1.0, "Rayleigh random number generator biased more than 1%"


## For interactive verification only 
# def plot_estimates():
#   from bokeh.io import output_notebook
#   from bokeh.plotting import show, figure
#   from bokeh.models import Span
#   output_notebook()
#   counts = np.array([np.sum(random.rademacher(100)) for _ in range(5000)])
#   # counts = np.array([np.sum(random.normal(100, engine="lcg")) for _ in range(5000)])
#   # counts = np.array([np.sum(random.rayleigh(100, engine="lcg")) for _ in range(5000)])
#   p = figure(width=200, height=150)
#   p.vbar(x=np.arange(len(counts)), top=counts, color="navy")
#   p.line(np.arange(1, len(counts)+1), np.cumsum(counts) / np.arange(1, len(counts)+1), color='red')
#   show(p)
