// Agentic verification layer for the assessment harness.
//
// The deterministic runners (r2/r3) emit candidate findings as JSONL. Workflow
// scripts CANNOT read files, so the driver reads results/*.jsonl, then passes the
// candidates in as `args`. Each candidate is adversarially verified by an
// independent panel; only findings a majority judges REAL survive.
//
// Invoke from Claude Code:
//   Workflow({ scriptPath: "<abs>/workflow/verify_findings.workflow.js",
//              args: [ {type:"bola", detail:"..."} , ... ] })

export const meta = {
  name: 'verify-findings',
  description: 'Adversarially verify candidate security findings from the runner JSONL.',
  whenToUse: 'After r2/r3 runners produce candidate findings; confirms real vs. false-positive.',
  phases: [{ title: 'Verify' }, { title: 'Synthesize' }],
};

const VERDICT = {
  type: 'object',
  additionalProperties: false,
  required: ['real', 'confidence', 'reason'],
  properties: {
    real: { type: 'boolean' },
    confidence: { type: 'number' },
    reason: { type: 'string' },
  },
};

const candidates = Array.isArray(args) ? args : [];
if (candidates.length === 0) {
  log('No candidates passed via args — nothing to verify.');
  return { confirmed: [], checked: 0 };
}

phase('Verify');
const verified = await pipeline(
  candidates,
  (c) =>
    parallel(
      ['correctness', 'authz-model', 'reproducibility'].map((lens) => () =>
        agent(
          `You are a skeptical AppSec reviewer using the ${lens} lens. A harness flagged this ` +
            `candidate finding against the target site:\n\n${JSON.stringify(c, null, 2)}\n\n` +
            `Default to real=false unless the evidence is unambiguous. Consider that a 200 may be ` +
            `a legitimately-shared/public resource, that 403≠leak, and that status alone rarely ` +
            `proves a cross-tenant read. Judge whether this is a REAL vulnerability.`,
          { label: `verify:${lens}`, phase: 'Verify', schema: VERDICT },
        ),
      ),
    ).then((votes) => {
      const real = votes.filter(Boolean);
      const yes = real.filter((v) => v.real).length;
      return { candidate: c, votes: real, real: yes >= 2 };
    }),
);

phase('Synthesize');
const confirmed = verified.filter(Boolean).filter((v) => v.real).map((v) => v.candidate);
log(`confirmed ${confirmed.length}/${candidates.length} candidates`);
return { confirmed, checked: candidates.length };
