# ${title}

This lab spins up a focused environment to practice **${concept_name}** in the context of the broader goal “${goal}”.

## Structure
- `docker-compose.yml` – services required for the lab
- `Makefile` – helper commands (`make up`, `make down`, `make logs`)
- `notes.md` – jot down findings and paste snippets back into the Teacher app

## Usage
1. Copy these files to a dedicated directory (or use the auto-generated path: `${output_path}`).
2. Run `make up` to start the stack.
3. Follow the exercise prompts provided by the Teacher app.
4. Tear down with `make down` when finished.

## Next Steps
Capture key learnings in `notes.md` and return the highlights to the chat so progress can be logged.
