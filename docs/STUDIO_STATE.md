# Studio state

Read and updated by the `/studio` skill so any session can pick up where the last one stopped.

```yaml
stage: pitch            # pitch | concept | design | build | slice-review | ship | released
mode: guided            # guided: human decides gates A and B | auto: creative-director decides them
pitch: ""
concept: ""
current_milestone: ""
gates:
  A_concept: pending
  B_vertical_slice: pending
  C_release: pending
```

## Log

- Studio set up: Godot 4.6.3 starter (third-person controller + smoke test), asset pipeline, CI.
