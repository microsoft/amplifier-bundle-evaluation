# SCRATCH ONLY -- never merged. Breaks `import amplifier_evaluation` so the
# workflow's `Import smoke` step is itself observed RED, independently of the
# lint and pytest steps (which are green/skipped in this variant).
raise ImportError("scratch: proving the CI import smoke step reports RED")
