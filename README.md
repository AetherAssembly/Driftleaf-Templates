# Driftleaf Vault Templates

Portable vault templates and template ideas for Driftleaf. Templates can
include Markdown notes and structured CSV or JSON data files. Each template
folder represents the vault root; copy its contents into a vault or package an
individual template folder as an archive. Driftleaf imports Markdown files from
ZIP archives and preserves their folder paths.

## Templates Built into Driftleaf

- **Blank**: no extra folders or notes. Driftleaf creates its standard
  `Welcome to Driftleaf` note for every new vault. This built-in option is not
  included as a downloadable ZIP.
- **General notes**: an inbox and project notes.
- **To-do / Productivity**: task lists, a project list, and an archive folder.
- **Journal**: a dated journal entry starter (`{{date}}` is the date
  placeholder).
- **Study**: course notes, an assignment tracker, and a study log.

These five templates mirror the starter note content built into Driftleaf.

## Additional standalone templates

The following are additional templates. They are included here as ordinary
files and are **not** registered or included in the Driftleaf app.

Download the ZIP archive for your preferred template from the [Releases page](https://github.com/AetherAssembly/Driftleaf-Templates/releases), then import it into Driftleaf.

- **Projects**: a general project portfolio and project brief.
- **Programming Project**: software project planning, implementation notes,
  decisions, and release checklist.
- **Work**: work priorities, ongoing responsibilities, and weekly reviews.
- **Meeting Notes**: a reusable agenda, discussion, decision, and action log.
- **Knowledge Base**: an index and evergreen article starter.
- **Habit Tracker**: a private daily habit log and review.
- **Period / Cycle Tracker**: a private, non-medical personal observation log.
- **Finance / Budget**: monthly budget and transaction tracking.
- **Meal Planner**: weekly meal planning and a grocery list.
- **D&D / Campaign**: campaign overview, sessions, locations, and NPCs.
- **Recipe Book**: recipe index and recipe card.
- **Travel Planner**: itinerary, reservations, packing, and trip notes.
- **Daily Planner**: a daily focus and schedule page.
- **To-Do / Task Management**: task inbox, projects, and review workflow.

[General Notes](general/), [Productivity](productivity/), [Journal](journal/), and
[Study](study/) are already represented by the templates currently in Driftleaf.
Feel free to create or modify any files, then make a PR for us to update the
files! Pull requests validate supported template files and produce
downloadable ZIP archives for each template folder.

The validation workflow accepts Markdown, CSV, and JSON files, validating
structured file syntax along with content for raw HTML and dangerous URL
schemes. It rejects other payloads and symlinks, then checks the generated ZIP
archives and SHA-256 checksums. Automated checks cannot determine whether
arbitrary template content is trustworthy, so human review is still required.
