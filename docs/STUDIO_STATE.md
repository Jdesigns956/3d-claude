# Studio state

Read and updated by the `/studio` skill so any session can pick up where the last one stopped.

```yaml
stage: brief            # brief | concept | build | review | deliver | done
mode: guided            # guided: human decides Gate A | auto: art-director decides it
kind: ""                # motion | model | both
brief: ""
slug: ""
direction: ""
piece: ""
gates:
  A_direction: pending
  C_release: pending
```

## Log

- Studio set up: Blender (headless) kit, two sample pieces (chrome_mandala_loop, mandala_medallion), asset and render queue.
