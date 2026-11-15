"""One interface for every model source. Each provider runs a whole conversation and returns
(assistant_replies, trace). `swap` (optional) = (turn_index, text): the assistant reply at that index is
replaced by `text` before the next user turn is sent (causal swap). Providers that cannot do this raise."""
import json, os, subprocess, time, uuid, urllib.request, glob, shutil

LIMIT_MARKERS = ("hit your", "usage limit", "rate limit", "FreeUsageLimitError", "quota")

class LimitHit(Exception): pass

def _check(text):
    t = (text or "").lower()
    if not t.strip(): raise RuntimeError("empty reply")
    if ("hit your" in t and "limit" in t) or "freeusagelimit" in t: raise LimitHit(text[:200])

# ---------------- Ollama (local, full visibility) ----------------
def ollama(model, system, user_turns, swap=None, opts=None):
    msgs = [{"role": "system", "content": system}]; replies = []; calls = []
    o = {"num_ctx": 16384, "num_predict": -1, "seed": 0}; o.update({k: v for k, v in (opts or {}).items() if k not in ("max_usd",)})
    # temperature and thinking: left at the model's defaults (pre-registered: default settings); seed = repeat index (set by run.py)
    for i, u in enumerate(user_turns):
        msgs.append({"role": "user", "content": u})
        body = {"model": model, "stream": False, "options": o, "messages": msgs}
        t0 = time.time()
        r = json.loads(urllib.request.urlopen(urllib.request.Request("http://localhost:11434/api/chat",
              data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}), timeout=900).read())
        text = r["message"]["content"]; _check(text)
        if r.get("done_reason") == "length": raise RuntimeError("reply cut off by length limit")
        calls.append({"request": body, "response": r, "secs": time.time() - t0})
        if swap and swap[0] == i: text_used = swap[1]
        else: text_used = text
        replies.append(text); msgs.append({"role": "assistant", "content": text_used})
    return replies, {"provider": "ollama", "calls": calls}

# ---------------- Claude Code through the sanitizing recorder ----------------
REC_PORT = int(os.environ.get("REC_PORT", "8787"))
MCP_EMPTY = os.path.join(os.path.dirname(__file__), "empty_mcp.json")
CLAUDE_WORKDIR = "/private/tmp/claude-501/mb_claude"

def _claude_session_file(sid):
    hits = glob.glob(os.path.expanduser(f"~/.claude/projects/*/{sid}.jsonl"))
    return hits[0] if hits else None

def _swap_claude_session(sid, new_text):
    """Replace the text of the LAST assistant message in a stored Claude Code session."""
    f = _claude_session_file(sid)
    if not f: raise RuntimeError("session file not found")
    lines = open(f).read().splitlines(); idx = None
    for j, l in enumerate(lines):
        try: r = json.loads(l)
        except Exception: continue
        if r.get("type") == "assistant": idx = j
    r = json.loads(lines[idx]); m = r["message"]
    m["content"] = [{"type": "text", "text": new_text}]
    lines[idx] = json.dumps(r); open(f, "w").write("\n".join(lines) + "\n")

def claude(model, system, user_turns, swap=None, opts=None):
    os.makedirs(CLAUDE_WORKDIR, exist_ok=True)
    sid = str(uuid.uuid4()); replies = []; calls = []
    env = dict(os.environ, ANTHROPIC_BASE_URL=f"http://127.0.0.1:{REC_PORT}")
    base = ["claude", "-p", "--model", model, "--tools", "", "--setting-sources", "", "--strict-mcp-config",
            "--mcp-config", MCP_EMPTY, "--exclude-dynamic-system-prompt-sections", "--system-prompt", system,
            "--output-format", "json"]
    for i, u in enumerate(user_turns):
        cmd = base + (["--session-id", sid] if i == 0 else ["--resume", sid]) + [u]
        t0 = time.time()
        p = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=CLAUDE_WORKDIR, stdin=subprocess.DEVNULL, timeout=900)
        try: out = json.loads(p.stdout)
        except Exception: raise RuntimeError("bad json: " + (p.stdout + p.stderr)[-300:])
        text = out.get("result", ""); _check(text)
        if out.get("is_error"): raise RuntimeError(text[:200])
        calls.append({"cli": out, "secs": time.time() - t0, "t_start": t0})
        replies.append(text)
        if swap and swap[0] == i: _swap_claude_session(sid, swap[1])
    return replies, {"provider": "claude_code+recorder", "session_id": sid, "calls": calls}

# ---------------- Codex CLI (ChatGPT login), harness disclosed ----------------
CODEX_HOME = "/private/tmp/claude-501/codexhome"
CODEX_FEATURES_OFF = ["multi_agent", "apps", "plugins", "skill_search", "shell_tool", "unified_exec",
                      "browser_use", "computer_use", "image_generation"]
CODEX_WORKDIR = "/private/tmp/claude-501/mb_codex"

def codex(model, system, user_turns, swap=None, opts=None):
    if swap: raise NotImplementedError("swap not supported for codex")
    os.makedirs(CODEX_WORKDIR, exist_ok=True); os.makedirs(CODEX_HOME, exist_ok=True)
    if not os.path.exists(f"{CODEX_HOME}/auth.json"): os.symlink(os.path.expanduser("~/.codex/auth.json"), f"{CODEX_HOME}/auth.json")
    instr = f"{CODEX_WORKDIR}/instr_{abs(hash(system))}.md"; open(instr, "w").write(system)
    eff = (opts or {}).get("effort", "medium")
    flags = sum([["-c", f"features.{f}=false"] for f in CODEX_FEATURES_OFF], [])
    common = flags + ["--ignore-rules", "--skip-git-repo-check", "-s", "read-only", "-m", model,
                      "-c", f"model_reasoning_effort={eff}", "-c", f"model_instructions_file={instr}", "--json"]
    env = dict(os.environ, CODEX_HOME=CODEX_HOME); replies = []; calls = []; tid = None
    for i, u in enumerate(user_turns):
        cmd = ["codex", "exec"] + common + [u] if i == 0 else ["codex", "exec", "resume", tid] + common + [u]
        t0 = time.time()
        p = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=CODEX_WORKDIR, stdin=subprocess.DEVNULL, timeout=900)
        ev = [json.loads(l) for l in p.stdout.splitlines() if l.startswith("{")]
        for e in ev:
            if e.get("type") == "thread.started": tid = tid or e["thread_id"]
        msgs = [e["item"]["text"] for e in ev if e.get("type") == "item.completed" and e["item"].get("type") == "agent_message"]
        usage = [e.get("usage") for e in ev if e.get("type") == "turn.completed"]
        if not msgs: raise RuntimeError("codex: " + (p.stdout + p.stderr)[-300:])
        text = msgs[-1]; _check(text)
        calls.append({"events": ev, "usage": usage, "secs": time.time() - t0}); replies.append(text)
    rollout = glob.glob(f"{CODEX_HOME}/sessions/**/*{tid}*.jsonl", recursive=True)
    return replies, {"provider": "codex_cli", "thread_id": tid, "rollout": rollout[0] if rollout else None, "calls": calls}

# ---------------- OpenRouter (clean API) ----------------
SPEND = os.path.expanduser("~/.mottebench_spend.jsonl")  # kept outside the repo; append-only, safe for many processes
def spend_total():
    t = 0.0
    if os.path.exists(SPEND):
        for l in open(SPEND):
            try: t += json.loads(l)["usd"]
            except Exception: pass
    return t
def _spend(model, usd, cap):
    """Append this call's reported cost (one line, under an exclusive file lock); raise LimitHit once the cap is reached.
    The cap check never discards a reply that was already paid for: it only stops the next call."""
    import fcntl
    with open(SPEND, "a") as f:
        fcntl.flock(f, fcntl.LOCK_EX); f.write(json.dumps({"model": model, "usd": usd, "ts": time.time()}) + "\n"); f.flush(); fcntl.flock(f, fcntl.LOCK_UN)
    return cap and spend_total() >= float(cap)

# Fixed serving host per model (pre-registered, Amendment 2.0): the model's own lab where OpenRouter offers it;
# otherwise a fixed fp8 host. Compressed (fp4) hosts are never used. No fallbacks to other hosts.
OR_HOSTS = {
    "openai/": ["OpenAI"], "anthropic/": ["Anthropic"], "google/": ["Google", "Google AI Studio"],
    "z-ai/glm-5.3": ["Z.AI"], "deepseek/deepseek-v4-pro": ["StreamLake", "Baidu"],
    "nvidia/": ["Nvidia"],
}
def _or_key():
    k = os.environ.get("OPENROUTER_API_KEY")
    if not k and os.path.exists(os.path.expanduser("~/.openrouter_env")):
        for line in open(os.path.expanduser("~/.openrouter_env")):
            if line.strip().startswith("OPENROUTER_API_KEY="): k = line.split("=", 1)[1].strip().strip("'\"")
    return k

def openrouter(model, system, user_turns, swap=None, opts=None):
    key = _or_key()
    if not key: raise RuntimeError("no OPENROUTER_API_KEY")
    msgs = [{"role": "system", "content": system}]; replies = []; calls = []
    cap = (opts or {}).get("max_usd")
    for i, u in enumerate(user_turns):
        if cap and spend_total() >= float(cap): raise LimitHit(f"spend cap {cap} reached")
        msgs.append({"role": "user", "content": u})
        body = {"model": model, "messages": msgs, "max_tokens": int((opts or {}).get("max_tokens", 32000)), "usage": {"include": True}}  # temperature: provider default
        hosts = (opts or {}).get("provider_order") or next((v for k, v in OR_HOSTS.items() if model.startswith(k)), None)
        body["provider"] = {"quantizations": ["fp8", "bf16", "fp16", "fp32", "unknown"], "allow_fallbacks": False, **({"order": hosts} if hosts else {})}
        req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=json.dumps(body).encode(),
              headers={"Content-Type": "application/json", "Authorization": "Bearer " + key})
        t0 = time.time(); r = json.loads(urllib.request.urlopen(req, timeout=900).read())
        text = r["choices"][0]["message"]["content"]; _check(text)
        if r["choices"][0].get("finish_reason") == "length": raise RuntimeError("reply cut off by length limit")
        calls.append({"request": body, "response": r, "served_by": r.get("provider"), "secs": time.time() - t0})
        _spend(model, (r.get("usage") or {}).get("cost") or 0.0, None)
        replies.append(text); msgs.append({"role": "assistant", "content": swap[1] if swap and swap[0] == i else text})
    return replies, {"provider": "openrouter", "calls": calls}

# ---------------- OpenCode free models ----------------
OC_ENV = {k: f"/private/tmp/claude-501/oc_{k.split('_')[1].lower()}" for k in
          ["XDG_DATA_HOME", "XDG_CONFIG_HOME", "XDG_STATE_HOME", "XDG_CACHE_HOME"]}

def opencode(model, system, user_turns, swap=None, opts=None):
    if swap: raise NotImplementedError("swap not supported for opencode")
    env = dict(os.environ, **OC_ENV); wd = "/private/tmp/claude-501/ocw"; os.makedirs(wd, exist_ok=True)
    replies = []; calls = []; sess = None
    for i, u in enumerate(user_turns):
        cmd = ["opencode", "run", "--pure", "-m", model, "--format", "json"] + (["-s", sess] if sess else []) + [u if i else system + "\n\n" + u]
        t0 = time.time()
        p = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=wd, stdin=subprocess.DEVNULL, timeout=900)
        ev = [json.loads(l) for l in p.stdout.splitlines() if l.startswith("{")]
        for e in ev: sess = sess or e.get("sessionID") or (e.get("part") or {}).get("sessionID")
        txt = "".join((e.get("part") or {}).get("text", "") for e in ev if (e.get("part") or {}).get("type") == "text")
        if not txt: raise RuntimeError("opencode: " + (p.stdout + p.stderr)[-300:])
        _check(txt); calls.append({"events": ev, "secs": time.time() - t0}); replies.append(txt)
    return replies, {"provider": "opencode_cli", "session": sess, "calls": calls,
                     "note": "system prompt prepended to first user turn; harness prompt of opencode default agent applies"}

PROVIDERS = {"ollama": ollama, "claude": claude, "codex": codex, "openrouter": openrouter, "opencode": opencode}
