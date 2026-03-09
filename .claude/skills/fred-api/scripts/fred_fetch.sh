#!/usr/bin/env bash
# FRED API client - Fetch economic data from the Federal Reserve
# Usage: bash fred_fetch.sh <command> [options]
# Requires: curl, FRED_API_KEY env var or .env file

set -euo pipefail

BASE_URL="https://api.stlouisfed.org/fred"

# --- Detect python command (python3 or python) ---
PYTHON=""
if python --version &>/dev/null; then
  PYTHON="python"
elif python3 --version &>/dev/null; then
  PYTHON="python3"
else
  echo "Error: python not found." >&2
  exit 1
fi

# --- Get API key ---
get_api_key() {
  if [[ -n "${FRED_API_KEY:-}" ]]; then
    echo "$FRED_API_KEY"
    return
  fi
  local env_file
  for env_file in ".env" "$(dirname "$0")/.env"; do
    if [[ -f "$env_file" ]]; then
      local key
      key=$(grep -E '^FRED_API_KEY=' "$env_file" | head -1 | cut -d= -f2- | tr -d "\"' ")
      if [[ -n "$key" ]]; then
        echo "$key"
        return
      fi
    fi
  done
  echo "Error: FRED_API_KEY not found. Set it as env var or in .env file." >&2
  exit 1
}

API_KEY=""

# --- HTTP request ---
fred_request() {
  local endpoint="$1"
  shift
  local url="${BASE_URL}/${endpoint}?api_key=${API_KEY}&file_type=json"
  for param in "$@"; do
    url="${url}&${param}"
  done
  local response http_code
  response=$(curl -sf --max-time 30 -w "\n%{http_code}" "$url" 2>/dev/null) || {
    echo "Error: Request failed for ${endpoint}" >&2
    exit 1
  }
  http_code=$(echo "$response" | tail -1)
  local body
  body=$(echo "$response" | sed '$d')
  if [[ "$http_code" -ge 400 ]]; then
    echo "Error: HTTP ${http_code}" >&2
    echo "$body" >&2
    exit 1
  fi
  echo "$body"
}

# --- Commands ---

cmd_search() {
  local query="" limit=20 order_by="popularity" sort_order="desc" format="table"
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --limit)     limit="$2"; shift 2 ;;
      --order-by)  order_by="$2"; shift 2 ;;
      --sort)      sort_order="$2"; shift 2 ;;
      --format)    format="$2"; shift 2 ;;
      -*)          echo "Unknown option: $1" >&2; exit 1 ;;
      *)           query="$1"; shift ;;
    esac
  done
  if [[ -z "$query" ]]; then
    echo "Usage: fred_fetch.sh search <query> [--limit N] [--order-by field] [--sort asc|desc] [--format table|json|csv]" >&2
    exit 1
  fi

  local encoded_query
  encoded_query=$(printf '%s' "$query" | curl -Gso /dev/null -w '%{url_effective}' --data-urlencode @- '' 2>/dev/null | cut -c3-)
  local data
  data=$(fred_request "series/search" "search_text=${encoded_query}" "limit=${limit}" "order_by=${order_by}" "sort_order=${sort_order}")

  local count
  count=$(echo "$data" | $PYTHON -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('seriess',[])))" 2>/dev/null || echo "0")

  if [[ "$count" == "0" ]]; then
    echo "No series found."
    return
  fi

  case "$format" in
    json)
      echo "$data" | $PYTHON -c "import sys,json; print(json.dumps(json.load(sys.stdin).get('seriess',[]),indent=2))"
      ;;
    csv)
      echo "$data" | $PYTHON -c "
import sys,json,csv
series=json.load(sys.stdin).get('seriess',[])
w=csv.DictWriter(sys.stdout,['id','title','frequency','units','seasonal_adjustment','last_updated','popularity'],extrasaction='ignore')
w.writeheader()
for s in series: w.writerow(s)
"
      ;;
    *)
      echo "$data" | $PYTHON -c "
import sys,json
series=json.load(sys.stdin).get('seriess',[])
total=json.load(open('/dev/stdin','r')) if False else None
print(f'Found {len(series)} series:\n')
print(f'{\"ID\":<25} {\"Title\":<50} {\"Freq\":<12} {\"Pop\"}')
print('-'*95)
for s in series:
    t=s.get('title','')
    if len(t)>48: t=t[:45]+'...'
    print(f'{s.get(\"id\",\"\"):<25} {t:<50} {s.get(\"frequency_short\",s.get(\"frequency\",\"\")):<12} {s.get(\"popularity\",\"\")}')
" <<< "$data"
      ;;
  esac
}

cmd_observations() {
  local series_id="" start="" end="" units="" frequency="" limit="" sort_order="asc" format="table"
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --start)     start="$2"; shift 2 ;;
      --end)       end="$2"; shift 2 ;;
      --units)     units="$2"; shift 2 ;;
      --frequency) frequency="$2"; shift 2 ;;
      --limit)     limit="$2"; shift 2 ;;
      --sort)      sort_order="$2"; shift 2 ;;
      --format)    format="$2"; shift 2 ;;
      -*)          echo "Unknown option: $1" >&2; exit 1 ;;
      *)           series_id="$1"; shift ;;
    esac
  done
  if [[ -z "$series_id" ]]; then
    echo "Usage: fred_fetch.sh observations <series_id> [--start YYYY-MM-DD] [--end YYYY-MM-DD] [--units lin|chg|pch|...] [--frequency d|m|q|a|...] [--format table|json|csv]" >&2
    exit 1
  fi

  local params=("series_id=${series_id}" "sort_order=${sort_order}")
  [[ -n "$start" ]]     && params+=("observation_start=${start}")
  [[ -n "$end" ]]       && params+=("observation_end=${end}")
  [[ -n "$units" ]]     && params+=("units=${units}")
  [[ -n "$frequency" ]] && params+=("frequency=${frequency}")
  [[ -n "$limit" ]]     && params+=("limit=${limit}")

  local data
  data=$(fred_request "series/observations" "${params[@]}")

  local count
  count=$(echo "$data" | $PYTHON -c "import sys,json; print(len(json.load(sys.stdin).get('observations',[])))" 2>/dev/null || echo "0")

  if [[ "$count" == "0" ]]; then
    echo "No observations found."
    return
  fi

  case "$format" in
    json)
      echo "$data" | $PYTHON -c "import sys,json; print(json.dumps(json.load(sys.stdin).get('observations',[]),indent=2))"
      ;;
    csv)
      echo "$data" | $PYTHON -c "
import sys,json,csv
obs=json.load(sys.stdin).get('observations',[])
w=csv.DictWriter(sys.stdout,['date','value'],extrasaction='ignore')
w.writeheader()
for o in obs: w.writerow({'date':o['date'],'value':o['value']})
"
      ;;
    *)
      $PYTHON -c "
import sys,json
data=json.load(sys.stdin)
obs=data.get('observations',[])
valid=[o for o in obs if o['value']!='.']
values=[float(o['value']) for o in valid]
print(f'Series: ${series_id}')
print(f'Observations: {len(obs)} ({obs[0][\"date\"]} to {obs[-1][\"date\"]})')
if values:
    print(f'Min: {min(values):.4f}  Max: {max(values):.4f}  Latest: {values[-1]:.4f}')
n=min(10,len(obs))
print(f'\nLast {n} observations:\n')
print(f'{\"Date\":<15} {\"Value\"}')
print('-'*30)
for o in obs[-n:]:
    print(f'{o[\"date\"]:<15} {o[\"value\"]}')
" <<< "$data"
      ;;
  esac
}

cmd_info() {
  local series_id="" format="table"
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --format) format="$2"; shift 2 ;;
      -*)       echo "Unknown option: $1" >&2; exit 1 ;;
      *)        series_id="$1"; shift ;;
    esac
  done
  if [[ -z "$series_id" ]]; then
    echo "Usage: fred_fetch.sh info <series_id> [--format table|json]" >&2
    exit 1
  fi

  local data
  data=$(fred_request "series" "series_id=${series_id}")

  case "$format" in
    json)
      echo "$data" | $PYTHON -c "import sys,json; s=json.load(sys.stdin).get('seriess',[]); print(json.dumps(s[0],indent=2) if s else 'Not found')"
      ;;
    *)
      $PYTHON -c "
import sys,json
s=json.load(sys.stdin).get('seriess',[])
if not s: print('Series not found.'); sys.exit()
s=s[0]
print(f'ID:                  {s.get(\"id\",\"\")}')
print(f'Title:               {s.get(\"title\",\"\")}')
print(f'Frequency:           {s.get(\"frequency\",\"\")}')
print(f'Units:               {s.get(\"units\",\"\")}')
print(f'Seasonal Adjustment: {s.get(\"seasonal_adjustment\",\"\")}')
print(f'Last Updated:        {s.get(\"last_updated\",\"\")}')
print(f'Observation Range:   {s.get(\"observation_start\",\"\")} to {s.get(\"observation_end\",\"\")}')
print(f'Popularity:          {s.get(\"popularity\",\"\")}')
notes=s.get('notes','')
if notes: print(f'Notes:               {notes[:200]}')
" <<< "$data"
      ;;
  esac
}

cmd_category() {
  local category_id="${1:-0}" format="table"
  shift 2>/dev/null || true
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --format) format="$2"; shift 2 ;;
      *)        shift ;;
    esac
  done

  local data
  data=$(fred_request "category/children" "category_id=${category_id}")

  case "$format" in
    json)
      echo "$data" | $PYTHON -c "import sys,json; print(json.dumps(json.load(sys.stdin).get('categories',[]),indent=2))"
      ;;
    *)
      $PYTHON -c "
import sys,json
cats=json.load(sys.stdin).get('categories',[])
if not cats: print('No child categories found.'); sys.exit()
print(f'{\"ID\":<10} {\"Name\":<50} {\"Parent ID\"}')
print('-'*70)
for c in cats:
    print(f'{c.get(\"id\",\"\"):<10} {c.get(\"name\",\"\"):<50} {c.get(\"parent_id\",\"\")}')
" <<< "$data"
      ;;
  esac
}

cmd_category_series() {
  local category_id="" limit=20 order_by="popularity" format="table"
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --limit)    limit="$2"; shift 2 ;;
      --order-by) order_by="$2"; shift 2 ;;
      --format)   format="$2"; shift 2 ;;
      -*)         echo "Unknown option: $1" >&2; exit 1 ;;
      *)          category_id="$1"; shift ;;
    esac
  done
  if [[ -z "$category_id" ]]; then
    echo "Usage: fred_fetch.sh category-series <category_id> [--limit N] [--format table|json|csv]" >&2
    exit 1
  fi

  local data
  data=$(fred_request "category/series" "category_id=${category_id}" "limit=${limit}" "order_by=${order_by}")

  case "$format" in
    json)
      echo "$data" | $PYTHON -c "import sys,json; print(json.dumps(json.load(sys.stdin).get('seriess',[]),indent=2))"
      ;;
    *)
      $PYTHON -c "
import sys,json
series=json.load(sys.stdin).get('seriess',[])
if not series: print('No series found.'); sys.exit()
print(f'{\"ID\":<25} {\"Title\":<50} {\"Freq\":<12} {\"Pop\"}')
print('-'*95)
for s in series:
    t=s.get('title','')
    if len(t)>48: t=t[:45]+'...'
    print(f'{s.get(\"id\",\"\"):<25} {t:<50} {s.get(\"frequency_short\",\"\"):<12} {s.get(\"popularity\",\"\")}')
" <<< "$data"
      ;;
  esac
}

# --- Usage ---
usage() {
  cat <<'USAGE'
FRED API Client - Fetch economic data from the Federal Reserve

Usage: fred_fetch.sh <command> [arguments]

Commands:
  search <query>              Search for series by keyword
    --limit N                 Max results (default: 20)
    --order-by FIELD          Sort field: popularity, search_rank, title, last_updated
    --sort asc|desc           Sort order (default: desc)
    --format table|json|csv   Output format (default: table)

  observations <series_id>    Get data points for a series
    --start YYYY-MM-DD        Start date
    --end YYYY-MM-DD          End date
    --units UNIT              Transform: lin, chg, ch1, pch, pc1, pca, cch, cca, log
    --frequency FREQ          Aggregate: d, w, bw, m, q, sa, a
    --limit N                 Max observations
    --sort asc|desc           Sort order (default: asc)
    --format table|json|csv   Output format (default: table)

  info <series_id>            Get series metadata
    --format table|json       Output format (default: table)

  category [category_id]      Browse categories (default: root)
    --format table|json       Output format (default: table)

  category-series <cat_id>    Get series in a category
    --limit N                 Max results (default: 20)
    --order-by FIELD          Sort field
    --format table|json|csv   Output format (default: table)

Environment:
  FRED_API_KEY                API key (or set in .env file)

Examples:
  fred_fetch.sh search "canada"
  fred_fetch.sh observations GDP --start 2020-01-01 --format csv
  fred_fetch.sh info UNRATE
  fred_fetch.sh category
USAGE
}

# --- Main ---
main() {
  if [[ $# -eq 0 ]]; then
    usage
    exit 0
  fi

  API_KEY=$(get_api_key)
  local command="$1"
  shift

  case "$command" in
    search)           cmd_search "$@" ;;
    observations|obs) cmd_observations "$@" ;;
    info)             cmd_info "$@" ;;
    category|cat)     cmd_category "$@" ;;
    category-series)  cmd_category_series "$@" ;;
    help|--help|-h)   usage ;;
    *)                echo "Unknown command: $command" >&2; usage; exit 1 ;;
  esac
}

main "$@"
