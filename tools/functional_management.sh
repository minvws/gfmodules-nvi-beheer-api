#!/usr/bin/env bash

set -euo pipefail

GREEN="\033[32m"
YELLOW="\033[33m"
BLUE="\033[34m"
CYAN="\033[36m"
BOLD="\033[1m"
DIM="\033[2m"
RED="\033[31m"
NC="\033[0m"

APP_URL="${FUNCTIONAL_MANAGEMENT_APP_URL:-http://localhost:8502}"
PROVIDERS_ENDPOINT="$APP_URL/healthcare-providers"
OUTPUT_FORMAT="json"

declare -A LIST_OPTION_MAP=(
    ["--oin"]="OIN_FILTER"
    ["--source-id"]="SOURCE_ID_FILTER"
    ["--ura-number"]="URA_NUMBER_FILTER"
)

declare -A PROVIDER_OPTION_MAP=(
    ["--ura-number"]="URA_NUMBER"
    ["--source-id"]="SOURCE_ID"
    ["--is-source"]="IS_SOURCE"
    ["--is-viewer"]="IS_VIEWER"
    ["--oin"]="OIN"
    ["--common-name"]="COMMON_NAME"
    ["--status"]="STATUS"
)

function usage() {
    echo -e "Usage: ./functional_management.sh <command> [options]\n"
    echo -e "Commands:"
    echo -e "  help                        Show this help message"
    echo -e "  list                        List all Zorgaanbieders"
    echo -e "  add    [options]            Add a new Zorgaanbieder"
    echo -e "  get    <id>                 Get a Zorgaanbieder by UUID"
    echo -e "  update <id> [options]       Update a Zorgaanbieder"
    echo -e "  remove <id> [-y|--yes]      Remove a Zorgaanbieder (skip confirmation)"
    echo -e "  set-url <url>               Print the export command to set the app URL"
    echo -e ""
    echo -e "Output format (for commands that return data):"
    echo -e "  --pretty-json               Pretty-print JSON output (default)"
    echo -e "  --table                     Render output as a table (if supported tools (jq and column, or miller, or python3) are available)"
    echo -e ""
    echo -e "Options for add / update:"
    echo -e "  --ura-number=<value>   URA number (max 8 digits)"
    echo -e "  --source-id=<value>    Source ID"
    echo -e "  --is-source=<true|false>  Whether this provider is a source"
    echo -e "  --is-viewer=<true|false>  Whether this provider is a viewer"
    echo -e "  --oin=<value>          OIN number"
    echo -e "  --common-name=<value>  Common name"
    echo -e "  --status=<value>       One of: active | soft-freeze | suspended | hard-blocked"
    echo -e ""
    echo -e "Filter options for list:"
    echo -e "  --oin=<value>         Filter providers by OIN (Max 20 characters)"
    echo -e "  --source-id=<value>   Filter providers by Source ID"
    echo -e "  --ura-number=<value>  Filter providers by URA number (Max 8 digits)"
    echo -e ""
    echo -e "App URL (current: ${CYAN}${APP_URL}${NC}):"
    echo -e "  Set via env var : ${DIM}export FUNCTIONAL_MANAGEMENT_APP_URL=<url>${NC}"
    echo -e "  Or run          : ${DIM}eval \$(./functional_management.sh set-url <url>)${NC}"
}

function usage_list() {
    echo -e "Usage: ./functional_management.sh list [filter options] [--pretty-json|--table]\n"
    echo -e "List Zorgaanbieders."
    echo -e ""
    echo -e "Filter options:"
    echo -e "  --oin=<value>         Filter providers by OIN (max 20 characters)"
    echo -e "  --source-id=<value>   Filter providers by Source ID"
    echo -e "  --ura-number=<value>  Filter providers by URA number (max 8 digits)"
}

function usage_add() {
    echo -e "Usage: ./functional_management.sh add [options] [--pretty-json|--table]\n"
    echo -e "Add a new Zorgaanbieder."
    echo -e ""
    echo -e "Required options:"
    echo -e "  --ura-number=<value>   URA number (max 8 digits)"
    echo -e "  --source-id=<value>    Source ID"
    echo -e "  --is-source=<true|false>"
    echo -e "  --is-viewer=<true|false>"
    echo -e "  --oin=<value>          OIN number"
    echo -e "  --common-name=<value>  Common name"
    echo -e "  --status=<value>       One of: active | soft-freeze | suspended | hard-blocked"
}

function usage_get() {
    echo -e "Usage: ./functional_management.sh get <id> [--pretty-json|--table]\n"
    echo -e "Get a Zorgaanbieder by UUID."
}

function usage_update() {
    echo -e "Usage: ./functional_management.sh update <id> [options] [--pretty-json|--table]\n"
    echo -e "Update a Zorgaanbieder."
    echo -e ""
    echo -e "Required options:"
    echo -e "  --ura-number=<value>   URA number (max 8 digits)"
    echo -e "  --source-id=<value>    Source ID"
    echo -e "  --is-source=<true|false>"
    echo -e "  --is-viewer=<true|false>"
    echo -e "  --oin=<value>          OIN number"
    echo -e "  --common-name=<value>  Common name"
    echo -e "  --status=<value>       One of: active | soft-freeze | suspended | hard-blocked"
}

function usage_remove() {
    echo -e "Usage: ./functional_management.sh remove <id> [-y|--yes]\n"
    echo -e "Remove a Zorgaanbieder by UUID."
    echo -e ""
    echo -e "Options:"
    echo -e "  -y, --yes  Skip confirmation prompt"
}

function usage_set_url() {
    echo -e "Usage: ./functional_management.sh set-url <url>\n"
    echo -e "Print the export command to set the app URL."
}

function is_help_arg() {
    local arg="${1:-}"
    [[ "$arg" == "--help" || "$arg" == "-h" ]]
}

function usage_for_command() {
    local cmd="${1:-}"
    case "$cmd" in
        list) usage_list ;;
        add) usage_add ;;
        get) usage_get ;;
        update) usage_update ;;
        remove) usage_remove ;;
        set-url) usage_set_url ;;
        *) usage ;;
    esac
}

function should_skip_health_check() {
    local cmd="${1:-}"
    shift || true

    [[ -z "$cmd" || "$cmd" == "help" || "$cmd" == "--help" || "$cmd" == "-h" || "$cmd" == "set-url" ]] && return 0
    has_help_arg "$@"
}

function die() {
    echo -e "${RED}Error: $*${NC}" >&2
    exit 1
}

MISSING_ARGS=()

function require_arg() {
    local flag="$1"
    local value="$2"
    if [[ -z "$value" ]]; then
        MISSING_ARGS+=("--${flag}")
    fi
}

function has_help_arg() {
    local arg
    for arg in "$@"; do
        if is_help_arg "$arg"; then
            return 0
        fi
    done

    return 1
}

function parse_long_options() {
    local map_name="$1"
    shift

    local -n option_map="$map_name"
    local arg flag value target_var

    while [[ $# -gt 0 ]]; do
        arg="$1"

        case "$arg" in
            --help | -h)
                return 10
                ;;
            --*=*)
                flag="${arg%%=*}"
                value="${arg#*=}"
                target_var="${option_map[$flag]:-}"

                [[ -n "$target_var" ]] || die "Unknown option: $arg"
                printf -v "$target_var" '%s' "$value"
                ;;
            --*)
                if [[ -n "${option_map[$arg]:-}" ]]; then
                    die "Use ${arg}=<value> instead of ${arg} <value>"
                fi
                die "Unknown option: $arg"
                ;;
            *)
                die "Unknown option: $arg"
                ;;
        esac

        shift
    done
}

function assert_no_missing_args() {
    if [[ ${#MISSING_ARGS[@]} -gt 0 ]]; then
        for arg in "${MISSING_ARGS[@]}"; do
            echo -e "${RED}Error: Missing required option: ${arg}${NC}" >&2
        done
        exit 1
    fi
}

function pretty_json() {
    if command -v python3 &>/dev/null; then
        python3 -m json.tool
    else
        cat
    fi
}

function render_output() {
    local json="$1"
    echo
    if [[ "$OUTPUT_FORMAT" == "table" ]]; then
        if command -v mlr &>/dev/null; then
            echo "$json" | mlr --ijson --opprint --barred cat
            return
        fi
        if command -v jq &>/dev/null && command -v column &>/dev/null; then
            echo "$json" | jq -r 'if type == "object" then [.] else . end | (.[0] | keys), (.[] | [.[] | tostring]) | @tsv' | column -t -s $'\t'
        elif command -v python3 &>/dev/null; then
            echo "$json" | python3 -c "
import json, sys

data = json.load(sys.stdin)
if isinstance(data, dict):
    data = [data]

if not data:
    print('(no results)')
    sys.exit(0)

keys = list(data[0].keys())
widths = {k: len(k) for k in keys}
for row in data:
    for k in keys:
        widths[k] = max(widths[k], len(str(row.get(k, ''))))

header = '  '.join(k.ljust(widths[k]) for k in keys)
sep    = '  '.join('-' * widths[k] for k in keys)
print(header)
print(sep)
for row in data:
    print('  '.join(str(row.get(k, '')).ljust(widths[k]) for k in keys))
"
        else
            echo -e "${YELLOW}Warning: No suitable tool found for table output. \n I tried miller, jq with column and python3. Falling back to pretty JSON.${NC}\n" >&2
            echo "$json" | pretty_json
        fi
    else
        echo "$json" | pretty_json
    fi
}

function http_request() {
    local method="$1"
    local url="$2"
    local data="${3:-}"

    if [[ -n "$data" ]]; then
        curl -s -w "\n%{http_code}" -X "$method" "$url" \
            -H "Content-Type: application/json" \
            -d "$data"
    else
        curl -s -w "\n%{http_code}" -X "$method" "$url"
    fi
}

function split_response() {
    local raw="$1"
    HTTP_CODE=$(echo "$raw" | tail -1)
    BODY=$(echo "$raw" | sed '$d')
}

function health_check() {
    echo -e "${GREEN}Performing health check...${NC}"
    if curl -s -f "$APP_URL/health" >/dev/null; then
        echo -e "${GREEN}App is healthy!${NC}"
    else
        echo -e "${YELLOW}App is not responding. Check if the app is running at ${APP_URL}${NC}"
        exit 1
    fi
}

function parse_list_args() {
    OIN_FILTER="" SOURCE_ID_FILTER="" URA_NUMBER_FILTER=""
    parse_long_options LIST_OPTION_MAP "$@"
}

function parse_provider_args() {
    URA_NUMBER="" SOURCE_ID="" IS_SOURCE="" IS_VIEWER="" OIN="" COMMON_NAME="" STATUS=""
    MISSING_ARGS=()

    parse_long_options PROVIDER_OPTION_MAP "$@"

    require_arg "ura-number"  "$URA_NUMBER"
    require_arg "source-id"   "$SOURCE_ID"
    require_arg "is-source"   "$IS_SOURCE"
    require_arg "is-viewer"   "$IS_VIEWER"
    require_arg "oin"         "$OIN"
    require_arg "common-name" "$COMMON_NAME"
    require_arg "status"      "$STATUS"
    assert_no_missing_args
}

function build_payload() {
    cat <<EOF
{
  "ura_number": "$URA_NUMBER",
  "source_id": "$SOURCE_ID",
  "is_source": $IS_SOURCE,
  "is_viewer": $IS_VIEWER,
  "oin": "$OIN",
  "common_name": "$COMMON_NAME",
  "status": "$STATUS"
}
EOF
}

function urlencode() {
    local string="$1"
    local encoded=""
    local pos c o

    for (( pos=0 ; pos<${#string} ; pos++ )); do
        c=${string:$pos:1}
        case "$c" in
            [a-zA-Z0-9.~_-]) o="$c" ;;
            *) printf -v o '%%%02X' "'$c" ;;
        esac
        encoded+="$o"
    done
    echo "$encoded"
}

function build_query_params() {
    local params=""
    [[ -n "$OIN_FILTER" ]] && params+="oin=$(urlencode "$OIN_FILTER")&"
    [[ -n "$SOURCE_ID_FILTER" ]] && params+="source_id=$(urlencode "$SOURCE_ID_FILTER")&"
    [[ -n "$URA_NUMBER_FILTER" ]] && params+="ura_number=$(urlencode "$URA_NUMBER_FILTER")&"
    echo "${params%&}"
}

function cmd_list() {
    if has_help_arg "$@"; then
        usage_list
        return
    fi

    parse_list_args "$@"

    echo -e "${GREEN}Getting all Zorgaanbieders...${NC}"
    local raw
    local query_params
    query_params=$(build_query_params)
    if [[ -n "$query_params" ]]; then
        raw=$(http_request GET "$PROVIDERS_ENDPOINT?$query_params")
    else
        raw=$(http_request GET "$PROVIDERS_ENDPOINT")
    fi
    split_response "$raw"

    case "$HTTP_CODE" in
        200) render_output "$BODY" ;;
        *)   echo -e "${RED}Failed (HTTP $HTTP_CODE):${NC}"; echo "$BODY"; exit 1 ;;
    esac
}

function cmd_add() {
    if has_help_arg "$@"; then
        usage_add
        return
    fi

    parse_provider_args "$@"

    echo -e "${GREEN}Adding a new Zorgaanbieder...${NC}"
    local raw
    raw=$(http_request POST "$PROVIDERS_ENDPOINT" "$(build_payload)")
    split_response "$raw"

    if [[ "$HTTP_CODE" -eq 200 || "$HTTP_CODE" -eq 201 ]]; then
        echo -e "${GREEN}Zorgaanbieder added successfully:${NC}"
        render_output "$BODY"
    else
        echo -e "${RED}Failed (HTTP $HTTP_CODE):${NC}"
        render_output "$BODY"
        exit 1
    fi
}

function cmd_get() {
    local id="${1:-}"
    if is_help_arg "$id" || [[ -z "$id" ]]; then
        usage_get
        [[ -n "$id" ]] && return
        exit 1
    fi

    echo -e "${GREEN}Getting Zorgaanbieder ${id}...${NC}"
    local raw
    raw=$(http_request GET "$PROVIDERS_ENDPOINT/$id")
    split_response "$raw"

    case "$HTTP_CODE" in
        200) render_output "$BODY" ;;
        404) echo -e "${YELLOW}Zorgaanbieder not found.${NC}"; exit 1 ;;
        *)   echo -e "${RED}Failed (HTTP $HTTP_CODE):${NC}"; echo "$BODY"; exit 1 ;;
    esac
}

function cmd_update() {
    local id="${1:-}"
    if is_help_arg "$id" || [[ -z "$id" ]]; then
        usage_update
        [[ -n "$id" ]] && return
        exit 1
    fi
    shift

    if has_help_arg "$@"; then
        usage_update
        return
    fi

    parse_provider_args "$@"

    echo -e "${GREEN}Updating Zorgaanbieder ${id}...${NC}"
    local raw
    raw=$(http_request PUT "$PROVIDERS_ENDPOINT/$id" "$(build_payload)")
    split_response "$raw"

    case "$HTTP_CODE" in
        200) echo -e "${GREEN}Zorgaanbieder updated successfully:${NC}"; render_output "$BODY" ;;
        404) echo -e "${YELLOW}Zorgaanbieder not found.${NC}"; exit 1 ;;
        *)   echo -e "${RED}Failed (HTTP $HTTP_CODE):${NC}"; render_output "$BODY"; exit 1 ;;
    esac
}

function cmd_remove() {
    local id="${1:-}"
    if is_help_arg "$id" || [[ -z "$id" ]]; then
        usage_remove
        [[ -n "$id" ]] && return
        exit 1
    fi

    local skip_confirm=false
    if [[ "${2:-}" == "-y" || "${2:-}" == "--yes" ]]; then
        skip_confirm=true
    fi

    echo -e "${YELLOW}Removing Zorgaanbieder ${id}...${NC}"
    if [[ "$skip_confirm" == false ]]; then
        read -rp "Are you sure? [y/N] " confirm
        [[ "$confirm" =~ ^[yY]$ ]] || { echo -e "${YELLOW}Aborted.${NC}"; exit 0; }
    fi

    local raw
    raw=$(http_request DELETE "$PROVIDERS_ENDPOINT/$id")
    split_response "$raw"

    case "$HTTP_CODE" in
        204) echo -e "${GREEN}Zorgaanbieder removed successfully.${NC}" ;;
        404) echo -e "${YELLOW}Zorgaanbieder not found.${NC}"; exit 1 ;;
        *)   echo -e "${RED}Failed (HTTP $HTTP_CODE):${NC}"; echo "$BODY"; exit 1 ;;
    esac
}
function cmd_set_url() {
    local url="${1:-}"
    if is_help_arg "$url" || [[ -z "$url" ]]; then
        usage_set_url
        [[ -n "$url" ]] && return
        exit 1
    fi
    echo "export FUNCTIONAL_MANAGEMENT_APP_URL=$url"
}

function main() {
    local cmd="${1:-}"
    if [[ -z "$cmd" ]]; then
        echo -e "${YELLOW}No command given.${NC}  Run with 'help' to see available commands."
        exit 1
    fi
    shift || true

    local filtered_args=()
    for arg in "$@"; do
        case "$arg" in
            --pretty-json) OUTPUT_FORMAT="json" ;;
            --table)       OUTPUT_FORMAT="table" ;;
            *)             filtered_args+=("$arg") ;;
        esac
    done
    set -- "${filtered_args[@]+"${filtered_args[@]}"}"

    case "$cmd" in
        help)
            if [[ $# -gt 0 ]]; then
                usage_for_command "$1"
            else
                usage
            fi
            ;;
        --help | -h) usage ;;
        list)   cmd_list   "$@" ;;
        add)    cmd_add    "$@" ;;
        get)    cmd_get    "$@" ;;
        update) cmd_update "$@" ;;
        remove)  cmd_remove  "$@" ;;
        set-url) cmd_set_url "$@" ;;
        *)
            echo -e "${RED}Unknown command: ${cmd}${NC}  (run 'help' for usage)"
            exit 1
            ;;
    esac
}

cmd="${1:-}"
if [[ -z "$cmd" || "$cmd" == "help" || "$cmd" == "--help" || "$cmd" == "-h" ]]; then
    echo -e "${BOLD}${CYAN}"
    echo -e "  ███╗   ██╗██╗   ██╗██╗    ██████╗ ███████╗██╗  ██╗███████╗███████╗██████╗ "
    echo -e "  ████╗  ██║██║   ██║██║    ██╔══██╗██╔════╝██║  ██║██╔════╝██╔════╝██╔══██╗"
    echo -e "  ██╔██╗ ██║██║   ██║██║    ██████╔╝█████╗  ███████║█████╗  █████╗  ██████╔╝"
    echo -e "  ██║╚██╗██║╚██╗ ██╔╝██║    ██╔══██╗██╔══╝  ██╔══██║██╔══╝  ██╔══╝  ██╔══██╗"
    echo -e "  ██║ ╚████║ ╚████╔╝ ██║    ██████╔╝███████╗██║  ██║███████╗███████╗██║  ██║"
    echo -e "  ╚═╝  ╚═══╝  ╚═══╝  ╚═╝    ╚═════╝ ╚══════╝╚═╝  ╚═╝╚══════╝╚══════╝╚═╝  ╚═╝"
    echo -e "${NC}"
    echo -e "  ${BOLD}Zorgaanbieder Management CLI${NC}  ${DIM}│  ${APP_URL}${NC}"
    echo -e ""
fi
if ! should_skip_health_check "$cmd" "${@:2}"; then
    health_check
    echo -e ""
fi
main "$@"
