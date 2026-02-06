# Progress Bars Quick Reference Card

## Installation
```bash
pip install -r requirements.txt
```

## Usage

### Run Demo
```bash
python scripts/demo_progress_bars.py
```

### Run Analysis
```bash
# Basic (5,000 sims, sequential)
python scripts/run_monte_carlo_analysis.py

# Custom simulations
python scripts/run_monte_carlo_analysis.py --simulations 10000

# Parallel execution
python scripts/run_monte_carlo_analysis.py --workers 4

# Full power
python scripts/run_monte_carlo_analysis.py --simulations 50000 --workers 8
```

## Progress Bar Output

### Simulation Progress
```
Monte Carlo Simulation:  45%|████████▌  | 4500/10000 [01:23<01:41, 54.12sim/s]
                         ^^^  ^^^^^^^^^  ^^^^^^^^^^^  ^^^^^^^^^^^^^^^  ^^^^^^^^
                          %   visual bar    count      time remaining   rate
```

### Visualization Progress
```
Creating charts:  56%|███████▏  | 5/9 [00:12<00:09, 0.44chart/s]
```

## Python Code

### Basic Usage
```python
from monte_carlo import MonteCarloEngine

# Sequential with progress
mc = MonteCarloEngine(n_simulations=5000, n_workers=1)
results = mc.run_simulation(verbose=True)

# Parallel with progress
mc = MonteCarloEngine(n_simulations=10000, n_workers=4)
results = mc.run_simulation(verbose=True)

# No progress
mc = MonteCarloEngine(n_simulations=1000)
results = mc.run_simulation(verbose=False)
```

### Custom Progress Bar
```python
from tqdm import tqdm

for item in tqdm(items, desc="Processing", unit="item"):
    process(item)
```

## Performance

| Mode       | Simulations | Workers | Time    | Rate      |
|------------|-------------|---------|---------|-----------|
| Sequential | 5,000       | 1       | ~90 sec | 55 sim/s  |
| Parallel   | 5,000       | 4       | ~30 sec | 165 sim/s |
| Parallel   | 10,000      | 4       | ~60 sec | 165 sim/s |

## Troubleshooting

### No progress bar shown
**Problem:** Only print statements appear
**Solution:** `pip install tqdm`

### Progress bar too wide
**Problem:** Doesn't fit terminal
**Solution:** Progress bar auto-adjusts to 100 characters

### Want to disable
**Solution:** Use `verbose=False` or set `TQDM_DISABLE=1`

## Files & Documentation

| File | Purpose |
|------|---------|
| `demo_progress_bars.py` | Interactive demo |
| `PROGRESS_BARS_README.md` | Full documentation |
| `PROGRESS_BARS_IMPLEMENTATION.md` | Technical details |
| `PROGRESS_BAR_SUMMARY.md` | Implementation summary |
| `PROGRESS_BARS_QUICK_REF.md` | This quick reference |

## Common Commands

```bash
# Quick test
python scripts/demo_progress_bars.py --simulations 100

# Show features only
python scripts/demo_progress_bars.py --features-only

# Parallel demo
python scripts/demo_progress_bars.py --workers 4

# Standard analysis
python scripts/run_monte_carlo_analysis.py

# Large analysis
python scripts/run_monte_carlo_analysis.py --simulations 50000 --workers 8
```

## Tips

- **Workers:** Use CPU cores - 1 (check with `python -c "import os; print(os.cpu_count())"`)
- **Simulations:** 5k-10k for standard, 50k+ for publication
- **Progress overhead:** <1% of runtime
- **Rate:** Higher is better (watch for bottlenecks)

---
**Quick start:** `python scripts/demo_progress_bars.py`
