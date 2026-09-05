"""Tier 4: AI-assisted resolution for records still unmatched or ambiguous
after Tiers 1-3.

Each case is sent to an LLM individually with structured context (amounts,
dates, references, and the fee/tax pattern already learned from Tier 1/2
matches) and forced structured output, so the response is real typed JSON,
not free text we hope to parse. Anything below config.AI_CONFIDENCE_THRESHOLD
is treated as "not matched" by the caller -- this module never silently
upgrades a low-confidence guess into a match.

Three providers are supported, auto-detected from the environment in this
priority order (first one found wins, so a judge's own ANTHROPIC_API_KEY
always wins if multiple are set):
  1. Anthropic Claude  (ANTHROPIC_API_KEY)              -- forced tool-call output
  2. Google Gemini     (GEMINI_API_KEY or GOOGLE_API_KEY) -- responseSchema JSON mode
  3. Groq              (GROQ_API_KEY)                    -- OpenAI-compatible forced tool-call output

Set FORCE_AI_PROVIDER=anthropic|gemini|groq to pin a specific provider
regardless of priority order (e.g. to verify each path independently even
when more than one key is configured) -- this mirrors passing an explicit
`provider=` argument, which always wins over both the env var and priority
order.

If none is configured, this tier degrades honestly: it reports itself
unavailable rather than fabricating a decision, and the caller routes those
records to exceptions with a clear reason.
"""
from __future__ import annotations

import json
import os
import re
import time

from . import config

_KEY_PATTERN = re.compile(r"(key=)[^&\s\"']+", re.IGNORECASE)

# name -> (env vars to check, in priority order)
_ENV_VARS_BY_PROVIDER = {
    "anthropic": ("ANTHROPIC_API_KEY",),
    "gemini": ("GEMINI_API_KEY", "GOOGLE_API_KEY"),
    "groq": ("GROQ_API_KEY",),
}
_PROVIDER_PRIORITY = ("anthropic", "gemini", "groq")


def _redact(text: str, *secrets: str | None) -> str:
    """Strip any literal API key (and any ?key=... query param) from a string
    before it can be written to the audit trail, a report, or a log line."""
    for secret in secrets:
        if secret:
            text = text.replace(secret, "***REDACTED***")
    return _KEY_PATTERN.sub(r"\1***REDACTED***", text)


def _is_daily_quota_exhausted(resp) -> bool:
    """Distinguish a per-day free-tier quota exhaustion (retrying/backing off
    won't help until tomorrow -- switch models instead) from an ordinary
    short-lived rate limit (worth retrying)."""
    try:
        body = resp.json()
        # Gemini returns status=RESOURCE_EXHAUSTED for every quota-type 429
        # (both per-minute and per-day), so that field alone can't
        # distinguish them. The quotaId in the violation details does --
        # only a "...PerDay..." quotaId means retrying won't help today.
        details = str(body.get("error", {}).get("details", []))
        return "PerDay" in details
    except Exception:
        return False


_RESULT_SCHEMA_PROPERTIES = {
    "match": {"type": "boolean", "description": "true if the target confidently corresponds to one or more candidates"},
    "matched_ids": {"type": "array", "items": {"type": "string"}, "description": "candidate record id(s) that match; empty if match is false"},
    "confidence": {"type": "number", "description": "0.0-1.0 confidence in this decision"},
    "reasoning": {"type": "string", "description": "concise human-readable justification"},
}
_REQUIRED_FIELDS = ["match", "matched_ids", "confidence", "reasoning"]

_MIN_GEMINI_CALL_SPACING_SECS = 12.0  # stay well under Gemini's low free-tier RPM limit
_last_gemini_call_at = [0.0]

_MIN_GROQ_CALL_SPACING_SECS = 1.0  # Groq's free tier is far more generous; a light guard is enough
_last_groq_call_at = [0.0]

_ANTHROPIC_TOOL = {
    "name": "resolve_match",
    "description": "Decide whether the target record matches one or more of the candidate records.",
    "input_schema": {"type": "object", "properties": _RESULT_SCHEMA_PROPERTIES, "required": _REQUIRED_FIELDS},
}

_GEMINI_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "match": {"type": "BOOLEAN"},
        "matched_ids": {"type": "ARRAY", "items": {"type": "STRING"}},
        "confidence": {"type": "NUMBER"},
        "reasoning": {"type": "STRING"},
    },
    "required": _REQUIRED_FIELDS,
}

# OpenAI-compatible function-calling schema, used for Groq's chat/completions API.
_OPENAI_TOOL = {
    "type": "function",
    "function": {
        "name": "resolve_match",
        "description": "Decide whether the target record matches one or more of the candidate records.",
        "parameters": {"type": "object", "properties": _RESULT_SCHEMA_PROPERTIES, "required": _REQUIRED_FIELDS},
    },
}


class AITier:
    def __init__(self, api_key: str | None = None, provider: str | None = None):
        self.provider = None
        self.model = None
        self._client = None  # anthropic client, when applicable
        self._gemini_key = None
        self._groq_key = None
        self._unavailable_reason = None

        # An explicit `provider` argument always wins; otherwise FORCE_AI_PROVIDER
        # pins one the same way (useful for verifying each path independently
        # without having to unset the other keys); otherwise fall through the
        # documented priority order.
        forced = provider or os.environ.get("FORCE_AI_PROVIDER")
        candidates = [forced] if forced else list(_PROVIDER_PRIORITY)

        for name in candidates:
            if name not in _ENV_VARS_BY_PROVIDER:
                continue
            # An explicit api_key is unambiguous when a single provider was
            # forced (provider= or FORCE_AI_PROVIDER). When no provider was
            # forced, an explicit api_key with no hint of which provider it
            # belongs to is tried against Anthropic first, matching this
            # module's original (pre-Groq) behavior, before falling through
            # to environment-based detection for the rest.
            key = api_key if (len(candidates) == 1 or name == "anthropic") else None
            if not key:
                for env_var in _ENV_VARS_BY_PROVIDER[name]:
                    key = os.environ.get(env_var)
                    if key:
                        break
            if not key:
                continue
            if self._activate(name, key):
                return

        if self._unavailable_reason is None:
            wanted = f"{forced} (via FORCE_AI_PROVIDER/provider)" if forced else "any of"
            env_vars = ", ".join(v for envs in _ENV_VARS_BY_PROVIDER.values() for v in envs)
            self._unavailable_reason = (
                f"no usable API key found for {wanted} -- checked {env_vars}"
                if forced else f"none of {env_vars} configured in environment"
            )

    def _activate(self, name: str, key: str) -> bool:
        if name == "anthropic":
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=key)
                self.provider, self.model = "anthropic", config.AI_MODEL
                return True
            except Exception as e:  # pragma: no cover - environment dependent
                self._unavailable_reason = f"anthropic client init failed: {e}"
                return False
        if name == "gemini":
            self._gemini_key = key
            self.provider, self.model = "gemini", config.GEMINI_MODEL
            return True
        if name == "groq":
            self._groq_key = key
            self.provider, self.model = "groq", config.GROQ_MODEL
            return True
        return False

    @property
    def available(self) -> bool:
        return self.provider is not None

    def resolve(self, case: dict) -> dict:
        """case: {record_id, source, amount, date, reference, candidates: [...], note}"""
        if not self.available:
            return {
                "match": False, "matched_ids": [], "confidence": 0.0,
                "reasoning": f"AI tier unavailable: {self._unavailable_reason}",
                "unavailable": True, "provider": None,
            }
        try:
            if self.provider == "anthropic":
                result = self._resolve_anthropic(case)
            elif self.provider == "groq":
                result = self._resolve_groq(case)
            else:
                result = self._resolve_gemini(case)
            result["unavailable"] = False
            result["provider"] = self.provider
            result.setdefault("matched_ids", [])
            result.setdefault("confidence", 0.0)
            return result
        except Exception as e:  # pragma: no cover - network/environment dependent
            safe_msg = _redact(str(e), self._gemini_key, self._groq_key)
            return {"match": False, "matched_ids": [], "confidence": 0.0,
                     "reasoning": f"AI call failed ({self.provider}): {safe_msg}", "unavailable": True,
                     "provider": self.provider}

    # ------------------------------------------------------------------
    def _resolve_anthropic(self, case: dict) -> dict:
        prompt = self._build_prompt(case)
        resp = self._client.messages.create(
            model=self.model,
            max_tokens=1024,
            tools=[_ANTHROPIC_TOOL],
            tool_choice={"type": "tool", "name": "resolve_match"},
            messages=[{"role": "user", "content": prompt}],
        )
        for block in resp.content:
            if block.type == "tool_use" and block.name == "resolve_match":
                return dict(block.input)
        return {"match": False, "matched_ids": [], "confidence": 0.0,
                "reasoning": "AI response did not include a tool call"}

    def _resolve_gemini(self, case: dict) -> dict:
        import requests
        prompt = self._build_prompt(case)
        headers = {"x-goog-api-key": self._gemini_key, "Content-Type": "application/json"}
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": _GEMINI_SCHEMA,
            },
        }

        # Google's free tier caps each model at a small number of requests/day.
        # If the current model's daily quota is exhausted, permanently switch
        # this AITier instance to the next candidate rather than burning
        # retries against a model that will keep returning 429 all day.
        models_to_try = [self.model] + [m for m in config.GEMINI_MODEL_FALLBACKS if m != self.model]
        last_exc = None

        for model in models_to_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
            max_attempts = 3
            quota_exhausted_for_model = False
            for attempt in range(max_attempts):
                # self-throttle: never fire two Gemini requests closer together
                # than _MIN_GEMINI_CALL_SPACING_SECS -- this is what actually
                # avoids 429s from a low free-tier RPM quota, not just
                # retrying after the fact.
                elapsed = time.monotonic() - _last_gemini_call_at[0]
                if elapsed < _MIN_GEMINI_CALL_SPACING_SECS:
                    time.sleep(_MIN_GEMINI_CALL_SPACING_SECS - elapsed)
                _last_gemini_call_at[0] = time.monotonic()
                try:
                    resp = requests.post(url, headers=headers, json=payload, timeout=30)
                    if resp.status_code == 429:
                        if _is_daily_quota_exhausted(resp):
                            last_exc = RuntimeError(f"daily free-tier quota exhausted for {model}")
                            quota_exhausted_for_model = True
                            break  # no point retrying this model further today
                        last_exc = RuntimeError("HTTP 429 from Gemini (rate limited)")
                        if attempt < max_attempts - 1:
                            time.sleep(20 + 10 * attempt)
                        continue
                    if resp.status_code in (500, 502, 503, 504):
                        last_exc = RuntimeError(f"HTTP {resp.status_code} from Gemini (transient)")
                        if attempt < max_attempts - 1:
                            time.sleep(min(2 ** attempt, 20))
                        continue
                    resp.raise_for_status()
                    data = resp.json()
                    text = data["candidates"][0]["content"]["parts"][0]["text"]
                    self.model = model  # stick with whichever model actually worked
                    return json.loads(text)
                except requests.RequestException as e:
                    last_exc = e
                    if attempt < max_attempts - 1:
                        time.sleep(min(2 ** attempt, 20))
            if not quota_exhausted_for_model:
                break  # a non-quota failure isn't fixed by switching models
        raise last_exc if last_exc else RuntimeError("Gemini call failed with no response")

    def _resolve_groq(self, case: dict) -> dict:
        import requests
        prompt = self._build_prompt(case)
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self._groq_key}", "Content-Type": "application/json"}
        base_payload = {
            "messages": [{"role": "user", "content": prompt}],
            "tools": [_OPENAI_TOOL],
            "tool_choice": {"type": "function", "function": {"name": "resolve_match"}},
        }

        # Same pattern as Gemini: if the current model is rate-limited hard
        # enough that Groq itself says "don't bother retrying for a while",
        # move to the next model rather than stalling this run on it.
        models_to_try = [self.model] + [m for m in config.GROQ_MODEL_FALLBACKS if m != self.model]
        last_exc = None

        for model in models_to_try:
            payload = {**base_payload, "model": model}
            max_attempts = 3
            give_up_on_model = False
            for attempt in range(max_attempts):
                elapsed = time.monotonic() - _last_groq_call_at[0]
                if elapsed < _MIN_GROQ_CALL_SPACING_SECS:
                    time.sleep(_MIN_GROQ_CALL_SPACING_SECS - elapsed)
                _last_groq_call_at[0] = time.monotonic()
                try:
                    resp = requests.post(url, headers=headers, json=payload, timeout=30)
                    if resp.status_code == 429:
                        retry_after = _groq_retry_after_seconds(resp)
                        last_exc = RuntimeError("HTTP 429 from Groq (rate limited)")
                        # A long mandated wait means switching models is cheaper
                        # than stalling this run on the same exhausted one.
                        if retry_after is not None and retry_after > 30:
                            give_up_on_model = True
                            break
                        if attempt < max_attempts - 1:
                            time.sleep(retry_after if retry_after is not None else 5 + 5 * attempt)
                        continue
                    if resp.status_code in (500, 502, 503, 504):
                        last_exc = RuntimeError(f"HTTP {resp.status_code} from Groq (transient)")
                        if attempt < max_attempts - 1:
                            time.sleep(min(2 ** attempt, 20))
                        continue
                    resp.raise_for_status()
                    data = resp.json()
                    message = data["choices"][0]["message"]
                    tool_calls = message.get("tool_calls") or []
                    for tc in tool_calls:
                        if tc.get("function", {}).get("name") == "resolve_match":
                            self.model = model  # stick with whichever model actually worked
                            return json.loads(tc["function"]["arguments"])
                    last_exc = RuntimeError("Groq response did not include a resolve_match tool call")
                except requests.RequestException as e:
                    last_exc = e
                    if attempt < max_attempts - 1:
                        time.sleep(min(2 ** attempt, 20))
            if not give_up_on_model:
                break
        raise last_exc if last_exc else RuntimeError("Groq call failed with no response")

    # ------------------------------------------------------------------
    @staticmethod
    def _build_prompt(case: dict) -> str:
        candidates_json = json.dumps(case["candidates"], indent=2)
        return f"""You are a financial reconciliation analyst for a payments company. A record from
the "{case['source']}" source could not be confidently matched by deterministic
rules (exact reference match, fuzzy match, or subset-sum grouping all failed
or were ambiguous). Decide whether it truly corresponds to one or more of the
candidate records below, using amount, date, and reference similarity.

Known deduction pattern learned from confidently-matched records so far:
net settlement amount is typically {config.NET_OF_GROSS_FACTOR:.4f} x gross amount
(Razorpay fee {config.RAZORPAY_FEE_RATE*100:.1f}% + GST on fee {config.FEE_GST_RATE*100:.0f}% + TDS {config.TDS_RATE*100:.1f}%).
This is a *typical* pattern, not an exact contract: real bank statements
sometimes carry a small additional service/processing charge (roughly
Rs 20-100, or a fraction of a percent) on top of it that isn't visible to
either source. Treat a small residual gap beyond the modelled deduction as
weak evidence at most, not disqualifying, if amount and date otherwise line
up closely and there is no competing candidate. In contrast, a mismatched or
unrelated reference/UTR when a candidate happens to share a similar amount
and date is a strong signal AGAINST a match, not for one -- do not let a
coincidental amount+date resemblance override a clear reference mismatch.

Target record:
  id: {case['record_id']}
  source: {case['source']}
  amount: {case['amount']}
  date: {case['date']}
  reference: {case.get('reference', 'N/A')}
  context: {case.get('note', 'none')}

Candidate records:
{candidates_json}

Be conservative: if no candidate is a genuinely strong match, set match=false
and confidence low. False positives (matching unrelated transactions) are
worse than false negatives (leaving something as an exception for human
review) -- only call match=true with high confidence when the evidence is
actually strong, not merely plausible."""


def _groq_retry_after_seconds(resp) -> float | None:
    """Groq (like most rate-limited APIs) tells you how long to wait --
    prefer that over guessing with a fixed backoff."""
    for header in ("retry-after", "Retry-After"):
        if header in resp.headers:
            try:
                return float(resp.headers[header])
            except ValueError:
                pass
    try:
        body = resp.json()
        msg = str(body.get("error", {}).get("message", ""))
        m = re.search(r"try again in ([\d.]+)s", msg, re.IGNORECASE)
        if m:
            return float(m.group(1))
    except Exception:
        pass
    return None
