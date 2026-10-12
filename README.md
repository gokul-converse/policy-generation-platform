1. Final proposed flow

Step 1 — User Input
One-line request, paragraph, PDF or document


Step 2 — Policy Generation Agent
Ollama / Open-source LLM
Understands the input and generates the initial policy draft.


Step 3 — Skill Selection UI
After the initial draft is generated, the user supplies skills or selects predefined skills.

Path A: Upload
User uploads their own skill files. The UI does not show the predefined skill list.


Path B: Select
If no custom skills are supplied, show predefined skills for the user to select.




Step 4 — Master Policy Generation Agent
Ollama / Open-source LLM
Combines the initial policy draft with the supplied or selected skill instructions to produce the master policy.


Step 5 — Master Policy Review
Display the policy as individual, selectable sections.

Select a section
Open a chat box for editing instructions.


Revision Agent / revision logic
Regenerate only the selected section using the user's instructions and relevant context.


Repeat until approved
Preserve other sections and maintain the updated master policy.




Step 6 — Foundry Agent
Azure AI Foundry model
Converts the approved master policy into the required structured JSON.


Step 7 — Final Web UI
Validate the JSON schema and render the resulting policy in the UI.


2. The skill-selection rule
This is the exact branching logic we'll implement.
Has the user uploaded custom skills?

Yes
Custom skills
Validate and process uploaded skills. Don't display the predefined list.


No
Predefined skills
Display the available skills and let the user select the relevant ones.



Both paths converge at master policy generation. The user explicitly determines which skills are used.





Policy Generation Workflow
1. Final Proposed Flow
Step 1 — User Input
One-line request
Paragraph
PDF or document
Step 2 — Policy Generation Agent
Model: Ollama / Open-source LLM
Understands the input and generates the initial policy draft
Step 3 — Skill Selection UI

After the initial draft is generated, the user supplies skills or selects predefined skills.

Path A: Upload

User uploads their own skill files
The UI does not show the predefined skill list

Path B: Select

If no custom skills are supplied, show predefined skills for the user to select
Step 4 — Master Policy Generation Agent
Model: Ollama / Open-source LLM
Combines the initial policy draft with the supplied or selected skill instructions to produce the master policy
Step 5 — Master Policy Review
Display the policy as individual, selectable sections
User selects a section
A chat box opens for editing instructions

Revision Agent / revision logic

Regenerates only the selected section using the user's instructions and relevant context
Repeat until approved
Preserves other sections and maintains the updated master policy
Step 6 — Foundry Agent
Model: Azure AI Foundry model
Converts the approved master policy into the required structured JSON
Step 7 — Final Web UI
Validates the JSON schema
Renders the resulting policy in the UI
2. The Skill-Selection Rule

This is the exact branching logic we'll implement.

Has the user uploaded custom skills?

Yes → Custom skills

Validate and process the uploaded skills
Don't display the predefined list

No → Predefined skills

Display the available skills
Let the user select the relevant ones

Both paths converge at master policy generation. The user explicitly determines which skills are used.