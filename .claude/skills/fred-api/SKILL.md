---
name: fred-api
description: "Fetch economic data from the FRED (Federal Reserve Economic Data) API. Search for series, retrieve observations, and explore economic datasets. Triggers on: FRED data, economic data, fetch FRED, FRED series, federal reserve data, FRED API."
---

# FRED API - Federal Reserve Economic Data

Fetch and explore economic data using the shell script at `.claude/skills/fred-api/scripts/fred_fetch.sh`.

---

## Prerequisites

- `curl` and python
- A FRED API key (free at https://fred.stlouisfed.org/docs/api/api_key.html)
- Set the key as environment variable `FRED_API_KEY` or in a `.env` file in the project root

---

## Step 1: Get the API Key

Before running any command, ensure the API key is available:
1. Check env var: `echo $FRED_API_KEY`
2. Check `.env` file in project root for `FRED_API_KEY=...`
3. If neither exists, ask the user for their key and set it: `export FRED_API_KEY=<key>`

**IMPORTANT:** Never hardcode or display the API key in output.

---

## Step 2: Run the Script

The script location is: `.claude/skills/fred-api/scripts/fred_fetch.sh`

All commands support `--format table|json|csv` for output control.

### Search for Series

```bash
bash .claude/skills/fred-api/scripts/fred_fetch.sh search "canada"
bash .claude/skills/fred-api/scripts/fred_fetch.sh search "GDP unemployment" --limit 10 --order-by search_rank
```

### Get Observations (Data Points)

```bash
bash .claude/skills/fred-api/scripts/fred_fetch.sh observations GDP
bash .claude/skills/fred-api/scripts/fred_fetch.sh observations UNRATE --start 2020-01-01 --end 2024-12-31
bash .claude/skills/fred-api/scripts/fred_fetch.sh observations GDP --units pch --frequency a --format csv
```

**Units transformations:** `lin` (levels), `chg` (change), `pch` (% change), `pc1` (% change YoY), `log` (natural log)
**Frequencies:** `d` (daily), `w` (weekly), `m` (monthly), `q` (quarterly), `a` (annual)

### Get Series Info

```bash
bash .claude/skills/fred-api/scripts/fred_fetch.sh info GDP
bash .claude/skills/fred-api/scripts/fred_fetch.sh info UNRATE --format json
```

### Browse Categories

```bash
bash .claude/skills/fred-api/scripts/fred_fetch.sh category            # root categories
bash .claude/skills/fred-api/scripts/fred_fetch.sh category 32992       # specific category
```

### Get Series in a Category

```bash
bash .claude/skills/fred-api/scripts/fred_fetch.sh category-series 32992 --limit 10
```

---

## Step 3: Save Data to File

Use `--format csv` or `--format json` with shell redirection:

```bash
bash .claude/skills/fred-api/scripts/fred_fetch.sh observations GDP --format csv > gdp_data.csv
bash .claude/skills/fred-api/scripts/fred_fetch.sh search "inflation" --format json > inflation_series.json
```

---

## Step 4: Present Results

- **Search results**: Show the table output directly or format as markdown
- **Observations**: The script auto-summarizes (date range, min/max/latest, last 10 values)
- **For deeper analysis**: Save as CSV, then use pandas or other tools in the project

---

## Common Series IDs

| Series ID | Description |
|-----------|-------------|
| `GDP` | US Gross Domestic Product |
| `UNRATE` | US Unemployment Rate |
| `CPIAUCSL` | Consumer Price Index (All Urban) |
| `FEDFUNDS` | Federal Funds Effective Rate |
| `DGS10` | 10-Year Treasury Rate |
| `SP500` | S&P 500 Index |
| `DEXCAUS` | Canada/US Exchange Rate |

---

## Error Handling

- **HTTP 401/403**: Invalid API key — ask user to verify
- **HTTP 429**: Rate limited — wait briefly and retry
- **No results**: Suggest broader search terms or verify series ID
