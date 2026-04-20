# Robot Mission - MAS 2025-2026

**Yoan Di Cosmo** - 2026-04-20

Mesa 3.x multi-agent simulation of robots collecting, transforming and disposing
of radioactive waste across three zones.

## Files

`objects.py` (Waste, Radioactivity, DisposalZone) - `agents.py` (Green/Yellow/Red
with pure `deliberate`) - `model.py` (grid, `do(action)`, message board) -
`server.py` (Solara viz) - `run.py` (single run + chart) - `batch_run.py`
(Step 1 vs Step 2 comparison over N seeds).

## Run

```bash
pip install -r requirements.txt

python run.py                      # single run, chart
python run.py --no-communication   # step 1
python batch_run.py --n-seeds 15   # step 1 vs step 2 boxplot
solara run server.py               # interactive viz
```

## Result (10 seeds, default scenario)

| Config                 | Mean steps | Std |
|------------------------|-----------:|----:|
| Step 1 (no comm)       |        186 | 209 |
| Step 2 (comm, global)  |         92 |  30 |
| Step 2 (comm, range=5) |         96 |  25 |

Communication gives ~2x speedup and cuts variance ~7x.
