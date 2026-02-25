#!/bin/bash
# Test the Financial Document Analyzer API
# Usage:
#   ./test.sh                          # Run all tests
#   ./test.sh submit                   # Submit a document
#   ./test.sh status <task_id>         # Check task status
#   ./test.sh full                     # Submit and poll until complete

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

BASE_URL="http://localhost:8000"
PDF_FILE="data/TSLA-Q2-2025-Update.pdf"
QUERY="Analyze this financial document for investment insights"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass() { echo -e "  ${GREEN}✓ $1${NC}"; }
fail() { echo -e "  ${RED}✗ $1${NC}"; }
info() { echo -e "  ${YELLOW}→ $1${NC}"; }

# ── Health check ──
test_health() {
    echo "Testing GET / ..."
    RESP=$(curl -s "$BASE_URL/")
    if echo "$RESP" | grep -q "running"; then
        pass "Health check passed"
    else
        fail "Health check failed: $RESP"
        return 1
    fi
}

# ── Submit document ──
test_submit() {
    local query="${1:-$QUERY}"
    echo "Testing POST /analyze ..."
    RESP=$(curl -s -X POST "$BASE_URL/analyze" \
        -F "file=@$PDF_FILE" \
        -F "query=$query")

    TASK_ID=$(echo "$RESP" | python3 -c "import json,sys; print(json.load(sys.stdin).get('task_id',''))" 2>/dev/null)
    STATUS=$(echo "$RESP" | python3 -c "import json,sys; print(json.load(sys.stdin).get('status',''))" 2>/dev/null)

    if [ "$STATUS" = "queued" ] && [ -n "$TASK_ID" ]; then
        pass "Document submitted — task_id: $TASK_ID"
        echo "$TASK_ID"
    else
        fail "Submit failed: $RESP"
        return 1
    fi
}

# ── Check status ──
test_status() {
    local task_id="$1"
    echo "Testing GET /status/$task_id ..."
    RESP=$(curl -s "$BASE_URL/status/$task_id")
    STATUS=$(echo "$RESP" | python3 -c "import json,sys; print(json.load(sys.stdin).get('status',''))" 2>/dev/null)
    
    case "$STATUS" in
        pending)    info "Status: pending (waiting in queue)" ;;
        processing) info "Status: processing (agents running)" ;;
        retrying)   info "Status: retrying (rate limited, will retry)" ;;
        success)
            ANALYSIS_LEN=$(echo "$RESP" | python3 -c "import json,sys; print(len(json.load(sys.stdin).get('analysis','')))" 2>/dev/null)
            pass "Status: success — analysis: $ANALYSIS_LEN chars"
            ;;
        failed)
            ERROR=$(echo "$RESP" | python3 -c "import json,sys; print(json.load(sys.stdin).get('error','')[:200])" 2>/dev/null)
            fail "Status: failed — $ERROR"
            ;;
        *)
            info "Status: $STATUS"
            ;;
    esac
    echo "$STATUS"
}

# ── Submit and poll until done ──
test_full() {
    echo "=== Full Integration Test ==="
    TASK_ID=$(test_submit 2>/dev/null | tail -1)
    if [ -z "$TASK_ID" ]; then
        fail "Failed to submit document"
        return 1
    fi
    pass "Submitted — task_id: $TASK_ID"

    echo ""
    echo "Polling status every 15s ..."
    while true; do
        STATUS=$(test_status "$TASK_ID" 2>/dev/null | tail -1)
        if [ "$STATUS" = "success" ]; then
            echo ""
            pass "Analysis complete!"
            echo ""
            curl -s "$BASE_URL/status/$TASK_ID" | python3 -c "
import json, sys
d = json.load(sys.stdin)
analysis = d.get('analysis', '')
print('Query:', d.get('query'))
print('Length:', len(analysis), 'chars')
print()
print('--- First 500 chars ---')
print(analysis[:500])
"
            break
        elif [ "$STATUS" = "failed" ]; then
            fail "Task failed"
            curl -s "$BASE_URL/status/$TASK_ID" | python3 -m json.tool
            break
        else
            info "Still $STATUS ... waiting 15s"
            sleep 15
        fi
    done
}

# ── Concurrent test ──
test_concurrent() {
    echo "=== Concurrent Requests Test ==="
    echo "Submitting 3 documents simultaneously..."

    PIDS=()
    for i in 1 2 3; do
        curl -s -X POST "$BASE_URL/analyze" \
            -F "file=@$PDF_FILE" \
            -F "query=Concurrent test $i" > "/tmp/concurrent_$i.json" &
        PIDS+=($!)
    done
    wait "${PIDS[@]}"

    for i in 1 2 3; do
        TID=$(python3 -c "import json; print(json.load(open('/tmp/concurrent_$i.json')).get('task_id','FAILED'))" 2>/dev/null)
        pass "Task $i queued: $TID"
    done
}

# ── Main ──
case "${1:-all}" in
    submit)
        test_submit "${2:-$QUERY}"
        ;;
    status)
        if [ -z "$2" ]; then
            fail "Usage: ./test.sh status <task_id>"
            exit 1
        fi
        test_status "$2"
        ;;
    full)
        test_health && test_full
        ;;
    concurrent)
        test_health && test_concurrent
        ;;
    all)
        echo "=== Quick Smoke Tests ==="
        test_health || exit 1
        echo ""
        TASK_ID=$(test_submit | tail -1)
        echo ""
        sleep 2
        test_status "$TASK_ID" > /dev/null
        echo ""
        test_concurrent
        echo ""
        echo "=== All smoke tests passed ==="
        echo "Run './test.sh full' for a complete end-to-end test (waits for analysis to finish)"
        ;;
    *)
        echo "Usage: ./test.sh [all|submit|status <task_id>|full|concurrent]"
        ;;
esac
