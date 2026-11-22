# Working in STOPReplay

Read the root README.md before editing. It defines team ownership, branch names, the proposed data handoff, and the first integration check. Inspect the current checkout for implementation details and commands. Coordinate shared-field changes with the owner of the consuming module.

## Frontend iterations

Frontend work is maintained on the `frontend` branch, separately from `integration`.

The user requested a preserved original and an independent experimental copy. Make future frontend changes in `frontend-clone/` unless the user explicitly asks to change the original. Keep `frontend/` intact.

- Original: `frontend/`, local port 5188.
- Active clone: `frontend-clone/`, local port 5190.

Both have their own source, assets, dependencies, and build output. Run frontend commands from the appropriate folder.
