# Enhanced Dashboard User Guide

## Quick Start

The USS/Nippon Steel dashboard now features **on-demand calculations** with intelligent caching, giving you full control over which analyses to run.

---

## Key Improvements

### ⚡ Faster Page Load
- **Before:** 30+ seconds waiting for everything to calculate
- **Now:** 2-5 seconds - only the main model runs automatically

### 🎮 User Control
- Choose which analyses to run
- See time estimates before calculating
- Results cached until parameters change

### 💾 Persistence
- Calculations survive browser refresh
- Auto-saves to disk
- Smart cache invalidation

### 📊 Progress Tracking
- Real-time progress bars
- Accurate percentages (0-100%)
- Descriptive status messages

---

## Using On-Demand Sections

### Scenario Comparison

**Location:** After synergy analysis section

**What it does:** Compares 6 preset scenarios (Base, Conservative, Management, etc.)

**How to use:**
1. Click **"Compare Scenarios"** button
2. Wait 5-15 seconds (progress bar shows status)
3. Results appear automatically
4. Change parameters → Button shows "Recalculate"

**Status Messages:**
- 🔵 "Click to compare scenarios (5-15 second calculation)" - Not yet calculated
- ✅ "Calculated at [timestamp]" - Results ready, up-to-date
- ⚠️ "Parameters changed. Click Recalculate to update." - Results outdated

---

### Probability-Weighted Valuation

**Location:** After scenario comparison

**What it does:** Weights scenarios by historical frequency to calculate expected value

**How to use:**
1. Click **"Calculate Expected Value"** button
2. Wait 8-12 seconds
3. View weighted metrics and scenario breakdown

**Includes:**
- Expected USS value (standalone)
- Expected Nippon value
- Expected 10-year FCF
- Scenario-by-scenario breakdown table

---

### Steel Price Sensitivity

**Location:** Bottom of dashboard

**What it does:** Tests 9 price levels (60%-150% of baseline)

**How to use:**
1. Click **"Run Price Sensitivity"** button
2. Wait 10-15 seconds
3. View:
   - Left chart: Share value vs price level
   - Right chart: Price projections by segment

**Use case:** Understand how sensitive valuation is to steel price assumptions

---

### WACC Sensitivity

**Location:** After steel price sensitivity

**What it does:** Tests WACC range from 5% to 14%

**How to use:**
1. Click **"Run WACC Sensitivity"** button
2. Wait 3-5 seconds
3. View chart with reference lines:
   - Blue line: USS WACC (~10.9%)
   - Red line: Nippon WACC (~7.5%)
   - Green line: $55 offer price

**Use case:** See how discount rate affects valuation

---

## Bulk Operations (Sidebar)

### Calculate All

**What it does:** Runs all 4 on-demand sections sequentially

**How to use:**
1. Click **"Calculate All"** button in sidebar
2. Watch overall progress bar
3. All sections calculated in ~30-40 seconds
4. Success message when complete

**Use case:**
- Initial analysis setup
- After changing multiple parameters
- Preparing comprehensive report

### Clear All

**What it does:** Removes all cached calculations

**How to use:**
1. Click **"Clear All"** button in sidebar
2. Confirmation message appears
3. All sections reset to "not calculated" state

**Use case:**
- Switching to different scenario entirely
- Freeing up memory
- Starting fresh analysis

---

## Understanding Status Indicators

### Button Colors
- **Blue (Primary):** Not calculated OR data is stale - click to calculate
- **Gray (Secondary):** Calculation is up-to-date - click to recalculate if desired

### Status Messages

**Not Calculated:**
```
ℹ️ Click to compare scenarios (5-15 second calculation)
```
- Section has never been calculated
- Estimate shows expected calculation time

**Up to Date:**
```
✅ Calculated at 2026-01-28 10:30:45
```
- Results are current
- Timestamp shows when calculation ran

**Stale (Parameters Changed):**
```
⚠️ Parameters changed. Click Recalculate to update.
```
- You changed prices, volumes, or other assumptions
- Cached results may no longer reflect current parameters
- Button highlighted in blue to draw attention

---

## Memory Management (Sidebar)

### Cache Usage Display

**What you see:**
- **Memory Cache:** Size of calculations in browser memory
- **Disk Cache:** Size of files saved to disk
- **Breakdown:** Click to see size by section

**Example:**
```
Memory Cache: 12.3 MB
Disk Cache: 15.1 MB

Breakdown:
- Scenario Comparison: 5.2 MB
- Probability Weighted: 3.1 MB
- Price Sensitivity: 2.5 MB
- WACC Sensitivity: 1.5 MB
```

### Memory Warning

If memory cache exceeds 50 MB:
```
⚠️ Memory cache is large. Consider clearing unused calculations.
```

**What to do:**
- Click "Clear All" to free up memory
- Only calculate sections you need
- Use "Calculate All" only when necessary

---

## Cache Behavior

### When Cache Invalidates (Auto-Clear)

Calculations clear automatically when you change:
- Steel price factors (HRC, CRC, Coated, OCTG)
- Volume factors or growth adjustments
- WACC assumptions
- Terminal growth rate
- Exit multiples
- Capital projects (enabled/disabled)
- Execution factor

**Why?** Cached results would no longer match your new assumptions.

### When Cache Persists

Calculations survive:
- Browser refresh
- Closing and reopening dashboard
- Scrolling through sections
- Toggling expanders

**How?** Results auto-save to disk in `./cache/` directory.

### Manual Cache Control

- **Clear specific section:** Click "Recalculate" (overwrites cache)
- **Clear all sections:** Click "Clear All" button
- **Calculate all sections:** Click "Calculate All" button

---

## Progress Bars Explained

### Main Model Calculation (Always Runs)

**What you see:**
```
Loading financial model... (0%)
Projecting Flat-Rolled segment... (15%)
Projecting Mini Mill segment... (25%)
Projecting USSE segment... (35%)
Projecting Tubular segment... (40%)
Calculating WACC... (45%)
Analyzing financing requirements... (55%)
Running USS valuation... (65%)
Building synergy schedule... (67%)
Running Nippon valuation... (82%)
Assembling results... (97%)
Analysis complete (100%)
```

**Duration:** 2-5 seconds typically

### On-Demand Calculations

**Scenario Comparison:**
```
Calculating scenario: BASE (1/6)
Calculating scenario: CONSERVATIVE (2/6)
...
```

**Probability-Weighted:**
```
Calculating scenario: Severe Downturn (1/5)
Calculating scenario: Downside (2/5)
...
```

**Steel Price Sensitivity:**
```
Testing price level: 60% of baseline (1/9)
Testing price level: 70% of baseline (2/9)
...
```

**WACC Sensitivity:**
```
Testing WACC: 5.0% (1/18)
Testing WACC: 5.5% (2/18)
...
```

---

## Best Practices

### Initial Setup

1. **Set your assumptions** in sidebar (prices, volumes, projects)
2. **Review main model results** (loads automatically)
3. **Click "Calculate All"** to run comprehensive analysis
4. **Wait ~30-40 seconds** for all sections to complete
5. **Review all results** - everything is cached now

### Exploring Scenarios

1. **Change one parameter** at a time
2. **Note the warning** on affected sections
3. **Click "Recalculate"** on sections you want to update
4. **Skip unnecessary** recalculations to save time

### Before Exporting

1. **Run "Calculate All"** to ensure everything is current
2. **Verify timestamps** on all sections
3. **Check for warnings** (stale data indicators)
4. **Export model** with complete results

### Memory Management

1. **Clear All** when switching scenarios entirely
2. **Calculate only what you need** for quick analysis
3. **Watch memory indicator** in sidebar
4. **Clear cache** if over 50 MB

---

## Troubleshooting

### "Parameters changed" warning won't go away

**Solution:** Click "Recalculate" button on that section.

**Why:** You changed parameters after last calculation. Recalculating updates the cache.

---

### Browser refresh lost my calculations

**Check:**
1. Did parameters change between sessions?
2. Is disk cache enabled? (should be automatic)
3. Check `./cache/` directory exists

**Solution:** Click "Calculate All" to regenerate.

---

### Progress bar stuck at 0%

**Likely cause:** Calculation is fast, progress bar updating slower than computation.

**Action:** Wait a few seconds. Progress bars auto-clear when done.

---

### Memory warning appearing

**Meaning:** You have >50 MB cached calculations.

**Solutions:**
1. Click "Clear All" to free memory
2. Calculate only needed sections
3. Refresh browser (clears session memory, keeps disk cache)

---

### Calculation seems slower than estimate

**Possible causes:**
- Complex scenario (many projects enabled)
- Higher execution factor (more iterations)
- System resource constraints

**Action:** Wait for completion. Time estimates are approximate.

---

## Keyboard Shortcuts

None currently implemented.

**Pro tip:** Use browser find (Ctrl+F / Cmd+F) to search for specific sections or values.

---

## FAQ

**Q: Do I have to click buttons every time I load the page?**

A: No! Calculations are saved to disk. If you don't change parameters, results load from cache automatically.

---

**Q: What happens if I change parameters?**

A: Cached calculations are marked "stale" with a warning. You choose whether to recalculate.

---

**Q: Can I export without calculating everything?**

A: Yes, but exported Excel will only include sections you've calculated. Use "Calculate All" for complete export.

---

**Q: How do I know if my results are current?**

A: Check for:
- ✅ Green checkmark = current
- ⚠️ Warning symbol = stale
- Timestamps show when calculated

---

**Q: What if I just want quick results?**

A: Just review the main model (loads automatically). Skip on-demand sections unless needed.

---

**Q: What's the "Football Field" section doing?**

A: It still calculates automatically (not on-demand). We kept it auto-calculate because it uses the main model results.

---

**Q: Can I see what's cached on disk?**

A: Check the `./cache/` directory in the project folder. Files named like `calc_scenario_comparison_a1b2c3d4.pkl`.

---

**Q: How much disk space does caching use?**

A: Typically 10-30 MB total. Check "Disk Cache" indicator in sidebar for current size.

---

## Technical Details

### Cache Files Location
```
./cache/
├── calc_scenario_comparison_a1b2c3d4.pkl
├── calc_scenario_comparison_a1b2c3d4.json
├── calc_probability_weighted_a1b2c3d4.pkl
├── calc_probability_weighted_a1b2c3d4.json
...
```

### File Formats
- `.pkl` files: Pickled Python objects (results data)
- `.json` files: Metadata (timestamp, size, hash)

### Auto-Cleanup
- Old caches deleted when scenario hash changes
- No manual cleanup needed
- Can manually delete `./cache/` directory if needed

---

## Getting Help

**Issues or bugs:**
- Check DASHBOARD_ENHANCEMENTS_SUMMARY.md for technical details
- Report issues via normal channels

**Feature requests:**
- Selective export (choose which sections to export)
- Time remaining estimates during calculation
- Cancel button for long operations

---

## Summary

The enhanced dashboard gives you:
- ⚡ **Speed**: 90% faster page loads
- 🎮 **Control**: Choose what to calculate
- 💾 **Persistence**: Results survive refresh
- 📊 **Feedback**: Real-time progress bars
- 🧹 **Management**: Bulk operations and memory tracking

**Key Habit:** Use "Calculate All" for comprehensive analysis, individual buttons for targeted updates.

Enjoy your faster, more responsive dashboard! 🚀
