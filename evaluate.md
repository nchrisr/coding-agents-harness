# Evaluate a tool or rule before adopting it

A finding often proposes a tool, a hook or a rule. Before it goes in the harness, test it on a real
project: the same questions or tasks, with it and without it. A test like that can look fine while
measuring nothing, so these rules come first.

1. **Same setup in every arm.** Same model, prompt, repository commit, permissions and instructions.
   Only the thing being tested differs. Run each arm in a clean environment, not one that inherits
   the current session's settings, which can change how tools load.
2. **Block it in the control arm.** The control must not reach the tool another way: through the
   shell, a command on the PATH, or a config file it finds. Deny it explicitly.
3. **Prove the tool ran before reading any numbers.** In every treated run's transcript, the tool is
   called and returns real results, with no permission denials and no "not connected" status. If
   one run fails this, the results don't count: fix the setup and run it again. A permission rule
   can be silently ignored, for example in a folder the agent hasn't been told to trust.
4. **Grade blind.** A separate grader scores the answers without knowing which arm produced them,
   against an answer key checked against the code, not just the docs. Docs drift, and a key written
   from them marks correct answers wrong. Check the grader's corrections to the key, fix the key, and
   grade every arm again with it.
   **When there's no reliable key** (open-ended tasks, or a key you can't check), compare instead: the
   grader sees the outputs side by side, labelled only with random ids, and says which is better and
   why, with evidence from the outputs. Comparison needs no right answer.
5. **Measure what you care about.** Count cost and correctness, not just tool calls or time. Fewer
   calls can cost the same if each call brings more text into the context.
6. **Report the size.** Say how many runs per arm, and what wasn't tested (editing tasks, long
   sessions, other languages). Two runs show large differences, not small ones.

**Try variations, not one version.** A finding's first wording is rarely its best. Write two or three
variations of the proposed rule or tool setup, and include at least one that changes how the agent
works and one that changes what it's told about the subject. Run each on the same task, compare them
as above, then combine what helped from each into the version that goes in the harness. Keep the
losing variations and the reason they lost in the finding, so the next attempt doesn't repeat them.

A transcript check for Claude Code runs started with `claude -p --output-format stream-json --verbose`
(swap in the tool's name):

```bash
tool='mcp__example__tool'
for f in runs/with-*.jsonl; do
  calls=$(jq -r --arg t "$tool" 'select(.type=="assistant") | .message.content[]?
    | select(.type=="tool_use" and .name==$t) | .id' "$f" | wc -l)
  denied=$(grep -c "haven't granted\|requires approval\|permission" "$f")
  echo "$f calls=$calls denied=$denied"
done
```

Every treated run needs `calls` above 0 and `denied` at 0.

Write up the result in the finding: the numbers, what it found, and what it didn't cover. If it isn't
worth adopting, say what is worth borrowing from it.
