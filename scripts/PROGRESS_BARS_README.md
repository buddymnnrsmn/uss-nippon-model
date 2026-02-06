# Monte Carlo Progress Bar Documentation

This document describes the enhanced progress bar functionality for Monte Carlo simulation in the USS/Nippon Steel financial model.

## Features

### 1. **Sequential Simulation Progress**
When running Monte Carlo simulations sequentially (single-threaded), you'll see a detailed progress bar:

```
Monte Carlo Simulation:  45%|████████████▌             | 4500/10000 [01:23<01:41, 54.12sim/s]
```

**Features:**
- Real-time completion percentage
- Current iteration / total iterations
- Elapsed time / estimated remaining time
- Simulation rate (iterations per second)

### 2. **Parallel Simulation Progress**
When using multiple workers (`--workers` option), the progress bar tracks completion across all parallel processes:

```
Parallel MC Simulation:  68%|██████████████████▌        | 6800/10000 [00:42<00:18, 161.90sim/s]
```

**Benefits:**
- Automatic tracking across worker processes
- Shows combined progress from all workers
- Higher throughput rate displayed

### 3. **Visualization Generation Progress**
Chart creation is tracked with a separate progress bar:

```
Creating charts:  56%|███████████████▏            | 5/9 [00:12<00:09, 0.44chart/s]
```

**Tracks:**
- Number of charts created
- Estimated time remaining
- Chart generation rate

## Installation

Progress bars require the `tqdm` package:

```bash
pip install tqdm
```

Or install all requirements:

```bash
pip install -r requirements.txt
```

## Usage Examples

### Basic Usage
```bash
# Run with default settings (5,000 simulations, sequential)
python scripts/run_monte_carlo_analysis.py

# Specify number of simulations
python scripts/run_monte_carlo_analysis.py --simulations 10000
```

### Parallel Execution
```bash
# Use 4 worker processes
python scripts/run_monte_carlo_analysis.py --workers 4

# Large run with parallelization
python scripts/run_monte_carlo_analysis.py --simulations 50000 --workers 8
```

### Demo Script
```bash
# Quick demo of progress bar features
python scripts/demo_progress_bars.py

# Demo with custom parameters
python scripts/demo_progress_bars.py --simulations 1000 --workers 4

# Show only progress bar features
python scripts/demo_progress_bars.py --features-only
```

## Code Integration

### In Your Scripts

#### Sequential Simulation
```python
from monte_carlo import MonteCarloEngine

mc = MonteCarloEngine(
    n_simulations=10000,
    use_lhs=True,
    n_workers=1  # Sequential
)

# Progress bar shown automatically
results = mc.run_simulation(verbose=True)
```

#### Parallel Simulation
```python
mc = MonteCarloEngine(
    n_simulations=10000,
    use_lhs=True,
    n_workers=4  # Parallel with 4 workers
)

# Progress bar tracks all workers
results = mc.run_simulation(verbose=True)
```

#### Custom Progress Bar
```python
from tqdm import tqdm

tasks = [task1, task2, task3]

for task in tqdm(tasks, desc="Processing", unit="task"):
    task()
```

## Performance Notes

### Sequential vs Parallel

**Sequential (n_workers=1):**
- Simple progress tracking
- Best for debugging
- Typical rate: 50-100 sim/s

**Parallel (n_workers=4+):**
- Multi-process execution
- Better progress granularity with 4x workers chunks
- Typical rate: 150-300 sim/s (4 workers)

### Optimization Tips

1. **Choose worker count wisely:**
   - Rule of thumb: `n_workers = CPU cores - 1`
   - Too many workers adds overhead
   - Check with: `python -c "import os; print(os.cpu_count())"`

2. **Simulation count:**
   - Quick test: 500-1,000
   - Standard analysis: 5,000-10,000
   - Publication quality: 50,000-100,000

3. **Progress bar overhead:**
   - Minimal (<1% of runtime)
   - Disable with `verbose=False` if needed

## Customization

### Progress Bar Format

The default format is:
```
{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]
```

Customize in `monte_carlo_engine.py`:

```python
iterator = tqdm(
    range(self.n_simulations),
    desc="Your Description",
    unit="your_unit",
    ncols=100,  # Width in characters
    bar_format='custom format string'
)
```

### Disable Progress Bars

```python
# Disable all output
results = mc.run_simulation(verbose=False)

# Or suppress only progress bars (keep other output)
import os
os.environ['TQDM_DISABLE'] = '1'
```

## Troubleshooting

### Progress Bar Not Showing
**Problem:** No progress bar appears, only periodic print statements.

**Solution:** Install tqdm:
```bash
pip install tqdm
```

### Progress Bar Jumbled Output
**Problem:** Multiple progress bars overlap or create messy output.

**Solution:** This can happen in Jupyter notebooks. Use:
```python
from tqdm.auto import tqdm  # Auto-detects environment
```

### Progress Bar Too Wide/Narrow
**Problem:** Progress bar doesn't fit terminal width.

**Solution:** Adjust `ncols` parameter:
```python
tqdm(..., ncols=80)  # Fixed width
tqdm(..., ncols=None)  # Auto-detect terminal width
```

## Advanced Features

### Nested Progress Bars
Track both outer loop (scenarios) and inner loop (simulations):

```python
from tqdm import tqdm

scenarios = ['base', 'optimistic', 'pessimistic']

for scenario in tqdm(scenarios, desc="Scenarios", position=0):
    mc = MonteCarloEngine(n_simulations=1000)
    # Inner progress bar shown automatically
    results = mc.run_simulation(verbose=True)
```

### Progress with Statistics
Update progress bar with running statistics:

```python
pbar = tqdm(total=10000, desc="Simulating")
for i in range(10000):
    result = run_iteration()
    pbar.update(1)
    pbar.set_postfix({
        'mean': f'{running_mean:.2f}',
        'median': f'{running_median:.2f}'
    })
pbar.close()
```

### Progress to File
Redirect progress to a log file:

```python
from tqdm import tqdm
import sys

with open('progress.log', 'w') as f:
    for i in tqdm(range(10000), file=f):
        # Your code here
        pass
```

## Related Files

- `monte_carlo/monte_carlo_engine.py` - Core engine with progress tracking
- `scripts/run_monte_carlo_analysis.py` - Full analysis with visualizations
- `scripts/demo_progress_bars.py` - Interactive demo
- `requirements.txt` - Package dependencies

## References

- [tqdm documentation](https://tqdm.github.io/)
- [Monte Carlo simulation guide](../monte_carlo/README.md)
- [Distribution calibration](../monte_carlo/DISTRIBUTION_CALIBRATION.md)
