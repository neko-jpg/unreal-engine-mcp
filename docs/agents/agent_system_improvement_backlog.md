# Agent System Improvement Backlog

This backlog records 100 concrete candidate improvements discovered during the
Rust-to-Python procedural migration and multi-agent architecture review. P0/P1
items marked `implemented` are covered by the current Python changes; the rest
are retained for staged delivery rather than hidden inside ad hoc notes.

1. P0 implemented: Add SQOP observation as the common quality evidence object.
2. P0 implemented: Add cave 12-shot survey planning from bounds, not hard-coded coordinates.
3. P0 implemented: Add deterministic metadata collection when Unreal is unavailable.
4. P0 implemented: Add cave math metrics for flatness, curvature, arch, detail, lighting.
5. P0 implemented: Add quality vector with explicit metric weights.
6. P0 implemented: Add cave quality gates as hard blockers.
7. P0 implemented: Add vision critique agent that consumes observation and math metrics.
8. P0 implemented: Add refinement compiler from evidence to parameter updates.
9. P0 implemented: Add refinement orchestrator loop.
10. P0 implemented: Add A/B comparison weighted 70 percent math, 30 percent VLM.
11. P0 implemented: Add scene-type protocol objects for cave, room, forest, city.
12. P0 implemented: Add cave graph generator in Python.
13. P0 implemented: Add SDF field construction from cave graph.
14. P0 implemented: Add domain warp and fBM roughness descriptors in Python.
15. P0 implemented: Add Python geometry AABB support.
16. P0 implemented: Add Python geometry OBB support.
17. P0 implemented: Add Python 2D segment intersection support.
18. P0 implemented: Add Python MCPM procedural mesh header contract.
19. P0 implemented: Add Python procedural mesh payload validation.
20. P0 implemented: Add Python procedural mesh binary serialization.
21. P0 implemented: Add Python SDF evaluator for sphere.
22. P0 implemented: Add Python SDF evaluator for box.
23. P0 implemented: Add Python SDF evaluator for capsule.
24. P0 implemented: Add Python SDF evaluator for torus.
25. P0 implemented: Add Python SDF evaluator for gyroid.
26. P0 implemented: Add Python SDF evaluator for scherk.
27. P0 implemented: Add Python SDF union support.
28. P0 implemented: Add Python SDF difference support.
29. P0 implemented: Add Python SDF intersection support.
30. P0 implemented: Add Python SDF domain warp support.
31. P0 implemented: Add Python SDF displacement/fBM support.
32. P0 implemented: Add Python SDF bounds estimation.
33. P0 implemented: Add Python SDF normal estimation.
34. P0 implemented: Add Python voxel-surface extraction as local fallback.
35. P0 implemented: Add Python L-system derivation.
36. P0 implemented: Add Python L-system turtle interpretation.
37. P0 implemented: Add Python 3D turtle yaw/pitch/roll controls.
38. P0 implemented: Add Python WFC adjacency construction.
39. P0 implemented: Add Python WFC entropy-based solver.
40. P0 implemented: Add Python WFC periodic-grid support.
41. P0 implemented: Add Python superformula mesh generation.
42. P0 implemented: Add Python superformula UV generation.
43. P0 implemented: Add scene_procedural_tools Python fallback for SDF.
44. P0 implemented: Add scene_procedural_tools Python fallback for superformula.
45. P0 implemented: Add scene_procedural_tools Python fallback for L-system.
46. P0 implemented: Add scene_procedural_tools Python fallback for WFC.
47. P0 implemented: Add multi-agent collaboration blackboard.
48. P0 implemented: Add orchestration decision object.
49. P0 implemented: Add supervisor/handoff/critic-loop mode selection.
50. P0 implemented: Add collaboration task snapshots in orchestrator output.
51. P0 implemented: Add agent observation records to shared state.
52. P0 implemented: Add evidence extraction from quality/validation outputs.
53. P0 implemented: Add reflection summary for failed agents and warning pressure.
54. P0 implemented: Add quality history memory entries.
55. P0 implemented: Add quality-gate guardrail diagnostics.
56. P0 implemented: Add quality dashboard CLI.
57. P1 implemented: Add material wetness/fBM metadata to cave material pass.
58. P1 implemented: Add cave PCG non-uniform Poisson field metadata.
59. P1 implemented: Add dramatic cave lighting metadata and light specs.
60. P1 implemented: Register vision critique agent in the agent system.
61. P1 implemented: Route quality/critique/vision domains to the critique agent.
62. P1 implemented: Preserve older scene-syncd realization path while adding Python fallback.
63. P1 pending: Replace voxel fallback with full Python marching cubes table.
64. P1 pending: Add Python mesh simplification before Unreal transfer.
65. P1 pending: Add Python mesh deduplication/weld pass.
66. P1 pending: Add Python tangent generation for procedural meshes.
67. P1 pending: Add material-id generation by SDF primitive source.
68. P1 pending: Add chunked mesh streaming for very large Python-generated meshes.
69. P1 pending: Add procedural result cache keyed by parameter hash.
70. P1 pending: Add automatic bounds scan before high-resolution SDF extraction.
71. P1 pending: Add SDF adaptive resolution by local curvature.
72. P1 pending: Add L-system preset parity with Rust preset file.
73. P1 pending: Add WFC contradiction explanation with minimal conflicting constraints.
74. P1 pending: Add WFC weighted entropy using tile weights during cell selection.
75. P1 pending: Add WFC rotations and symmetry classes.
76. P1 pending: Add superformula material bands by latitude/longitude.
77. P1 pending: Add local Python procedural dry-run endpoint wrappers.
78. P1 pending: Add procedural benchmark suite comparing Python and Rust outputs.
79. P1 pending: Add scene-syncd route deprecation map for generator endpoints.
80. P1 pending: Add migration flag to prefer Python generators by default.
81. P1 pending: Add launch-dev-stack smoke command with finite verification window.
82. P1 pending: Add launch-dev-stack JSON health summary output.
83. P1 pending: Add Unreal TCP command smoke test after editor readiness.
84. P1 pending: Add scene-syncd health endpoint browser verification.
85. P1 pending: Add MCP stdio liveness probe that does not require a client.
86. P2 pending: Add agent tool-cost model for route selection.
87. P2 pending: Add agent role reassignment when a specialist fails.
88. P2 pending: Add cross-agent memory TTL and compaction.
89. P2 pending: Add structured handoff contract per domain.
90. P2 pending: Add critic budget limits per iteration.
91. P2 pending: Add automatic retry with parameter perturbation.
92. P2 pending: Add population search for cave parameter optimization.
93. P2 pending: Add Bayesian optimization adapter.
94. P2 pending: Add CMA-ES adapter for numeric scene parameters.
95. P2 pending: Add screenshot feature embedding cache.
96. P2 pending: Add VLM provider abstraction for local/offline models.
97. P2 pending: Add agent trace export to OpenTelemetry JSON.
98. P2 pending: Add task-level replay from blackboard snapshots.
99. P2 pending: Add safety policy for destructive Unreal scene operations.
100. P2 pending: Add generated-scene regression dashboard across the last N runs.
