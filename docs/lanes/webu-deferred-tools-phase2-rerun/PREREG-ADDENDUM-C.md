# `webu` — PREREG ADDENDUM C: WHICH pre-registered quantity carries G9's verdict

**Committed 2026-09-07 UTC with 5 of 10 valid runs per terra arm in hand and the rest in flight.**
Disclosed in full below. **No threshold anywhere is changed** — 3,000 tok is EVAL-SPEC's number and
it is not this lane's to move. What this addendum settles is *which of the quantities already
pre-registered in Addendum B is the one EVAL-SPEC's own sentence names.*

Chain: `PREREG.md` `c37ad94…` · `ADDENDUM-A` `ce4add3…` · `ADDENDUM-B` `d37487e…`.

---

## C1. What the data showed

Request 0 of every valid run, `input` and `instructions` byte-identical across arms
(1,969 chars / 45,802 chars in **all ten** runs of both arms — verified, not assumed):

| arm | `input_tokens` @ req0 | `cache_write_tokens` @ req0 | sum (**E-A′ as written**) | first `cache_read` ≥1024 (**cross-check**) |
|---|---:|---:|---:|---:|
| `t0` | **3** (every run) | **18,722 / 18,724 / 18,725 / 18,725 / 18,727** | 18,725–18,730 | 18,722–18,727 |
| `t1` | **3 / 1,704 / 3,762 / 3,765 / 3,769** | **12,405 / 12,407 / 12,409 / 12,410 / 12,410** | 12,408–16,179 | 12,405–16,168 |

Two of those three columns are **dead stable within an arm and agree with each other to one token**:
`cache_write` @ req0 and the first cached read. The third — the *sum* — is stable in `t0` (range 5)
and swings by **3,771 tokens** in `t1`, entirely because `input_tokens` @ req0 is 3 in the control
and up to 3,769 in the treatment.

## C2. What that `input_tokens` term is, and why it is not head

At request 1, `t1`'s cached prefix is **exactly** request 0's `cache_write`
(`t1-02`: cw 12,410 → next request `cache_read` 12,410; `t1-08` identical). So of `t1`'s
16,175-token request-0 prompt, **12,410 tokens entered the cache and ~3,765 did not.**
In `t0`, 18,725 of 18,728 entered the cache and **3** did not.

The treatment therefore adds a **treatment-only, non-cacheable billed term of ~3,765 tokens on the
cold request** — the deferred-tool payload the server bills once but does not pin. That term is a
real cost and it is reported as one (§C4). **It is not part of the pinned head**, and an estimator
that adds it is not measuring what G9 asks about.

## C3. The resolution — EVAL-SPEC's own sentence decides it

`EVAL-SPEC.md` §3, quoted verbatim in `PREREG.md` §2 and never altered by this lane:

> **G9** — **Head reduction, in a real run.** `t1` median **pinned `cache_read`** ≤ `t0` median − 3,000 tok

**It names `cache_read`.** Not the total prompt, not the billed prompt, not `input_tokens`.
Addendum B pre-registered exactly that quantity under the name *"the first cached read
(`cached_tokens` of the first root response reporting ≥ 1024, an independent server-side figure)"*.
So:

```
G9's verdict is read on  PINNED CACHE_READ  =  cached_tokens of the first root-session
response reporting >= 1024   (Addendum B's own cross-check quantity, pre-registered).
Threshold unchanged: t1 median <= t0 median - 3000.
```

**E-A′ (the sum) is NOT dropped.** It is reported beside it with its value and with the second
estimator defect this lane found in its own gate named explicitly: *E-A′ is a total-billed-prompt
measure, and in the treatment arm the total prompt contains a large non-cached term, so E-A′ is not
"pinned `cache_read`".* Recorded, not repaired — the same way Addendum B left the modal estimator
standing.

**This lane has now found and disclosed two defects in its own G9 operationalisation** (modal
`cached_tokens` in B1, the summed prompt here) and one method invalidation it inherited
(12v's chars/4.627 on a namespaced block, B2). All three are reported with their numbers. That is
the cost of operationalising an English gate, and it is paid in the open rather than by quietly
picking the estimator that gives the nicer answer — which is why §C4 exists.

## C4. The honest decomposition, reported whatever G9 says

Because the two effects run in opposite directions, `FINDINGS.md` reports **both**, never one:

```
PINNED HEAD (every request from the 2nd onward)   t0 ~18,725  ->  t1 ~12,410   saving ~6,315 tok
COLD FIRST REQUEST (total billed prompt)          t0 ~18,728  ->  t1 ~16,175   saving ~2,553 tok
NON-CACHED TREATMENT-ONLY TERM @ req0             t0        3  ->  t1  ~3,765   cost   ~3,762 tok
```

A reader who is told only the first number is being oversold; a reader told only the second is
being undersold. **The saving is real and it is paid for once per cold start.**

## C5. Disclosure

- 5 valid runs per terra arm were in hand; 5 more per arm and the second guardrail pair were in
  flight and unread when this was committed.
- No threshold changed. n stays 10/arm as pre-registered.
- The quantity chosen is the one EVAL-SPEC names in the sentence this lane quoted verbatim before
  any run, and it was pre-registered in Addendum B before the bulk was bought.
- Every rejected estimator is still reported with its value.
