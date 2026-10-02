# Pathwise — Project 1 Proposal

CS 529 AI Engineering · Multi-Agent System with OpenAI Agents SDK · Oct 1, 2026 · @Leul Tsige

## Title and abstract

**Pathwise: a multi-agent system that turns "I want to learn X" into a researched roadmap and interactive lessons.**

Pathwise helps people in tech learn a new technology, framework or concept faster and with less noise. A user describes what they want to learn in plain language. A team of agents then clarifies the goal, researches the topic on the web, filters and fact-checks the sources, and builds a learning roadmap. A second team turns that roadmap into short, structured, interactive lesson pages.

Pathwise remembers each user's background, tech stack and learning preferences. The more someone uses it, the better tailored the roadmaps and lessons become. Researched sources are stored in a vector store, so later lessons and follow-up questions are grounded in vetted material rather than the model's memory.

## Key goals

1. **Learn a new technology efficiently.** Go from "never used it" to "can build something" in the fewest, most relevant steps.
2. **Create a roadmap.** Show the topic as an ordered map of subtopics, with prerequisites, so the learner knows where they are and what comes next.
3. **Keep content applicable and to the point.** Every lesson is comprehensive and structured, not verbose, and tied to the learner's own tech stack.
4. **Ground content in vetted sources.** Lessons cite the articles they came from, and a fact-checking step catches errors before the learner sees them.
5. **Run the agent workflow cost-effectively.** Use small models for simple steps, reuse research already stored, and cap web searches per request.
6. **Personalise through memory.** Remember each user's preferences, level and history so later sessions need less questioning.



## Expected features

A user types an unstructured request, answers a few clarifying questions, and gets back a roadmap plus interactive lessons they can study and ask follow-up questions about.

**Input**

- An unstructured prompt, for example: "I'm a Java/Spring dev and want to learn Kafka for event-driven microservices."
- Clarifying questions when the request is too vague: current level, tech stack, goal (job, project, exam), time available, preferred output format.

**Output**

- **Research artifacts:** a list of vetted articles, each with a short summary, source link, and a matching score.
- **Roadmap:** the topic broken into categorised subtopics with prerequisites (a topology), shown as an ordered path.
- **Lessons:** one page per roadmap step, with learning goals, preconditions (what you need to know first) and postconditions (what you can do afterwards).
- **Output format chosen by the user:** an HTML page rendered in the app (default), a downloadable HTML file, or React components (stretch goal).

**Memory and chats**

- Keep track of user preferences (level, stack, format, tone).
- Remember key points from each conversation, compressing older turns into a summary to save tokens.
- Keep several separate chats, one per learning topic, that the user can reopen.

**Follow-up tutoring**

- While on a lesson, the user can ask questions. A tutor agent answers from that lesson's stored sources (RAG) instead of starting a new research run.



## Agent roles

Thirteen agents in four teams. The team's notes are kept, with two merges: Fact Checker and Gap Finder become one **Critic**, and the four-agent Interactive Page team becomes **Converter + Verifier**. Agents pass typed objects to each other (Pydantic `output_type`), not free text.


| #   | Agent                      | Team          | Responsibility                                                                            | Input → Output                                                                    | Tools                                   | Model      |
| --- | -------------------------- | ------------- | ----------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- | --------------------------------------- | ---------- |
| 1   | Intake Agent (router)      | Front door    | Greets the user, asks clarifying questions, routes the request                            | Raw prompt + user profile → `LearningRequest` (topic, level, stack, goal, format) | `get_user_profile`, handoffs            | gpt-5-mini |
| 2   | Tutor Agent                | Front door    | Answers follow-up questions on an existing lesson                                         | Question + lesson id → grounded answer with citations                             | `FileSearchTool` (topic's vector store) | gpt-5-mini |
| 3   | Research Manager           | Research      | Orchestrates research and decides when it is good enough                                  | `LearningRequest` → `ResearchPack`                                                | Agents 4–8 as tools                     | gpt-5-mini |
| 4   | Topic Planner              | Research      | Splits the topic into search angles: theory, use cases, how-to for the user's stack       | `LearningRequest` → list of search queries                                        | none                                    | gpt-5-nano |
| 5   | Web Search Agent           | Research      | Finds candidate articles for one query                                                    | Query → list of (title, url, snippet)                                             | `WebSearchTool`                         | gpt-5-nano |
| 6   | Relevance Judge            | Research      | Scores whether each result matches the topic and level; drops weak ones                   | Topic + candidate → score 1–5 + keep/drop + reason                                | (Typesafe Jev)                          | gpt-5-nano |
| 7   | Summarizer                 | Research      | Summarises each kept article into key points                                              | Article → `ArticleSummary`                                                        | `WebSearchTool` (to read the page)      | gpt-5-nano |
| 8   | Critic (fact check + gaps) | Research      | Flags contradictions between sources and subtopics with no coverage                       | Summaries → `CritiqueReport` (issues, gaps)                                       | none                                    | gpt-5-mini |
| 9   | Roadmap Agent              | Learning plan | Builds the topology: categories, prerequisites, order                                     | `ResearchPack` → `Roadmap` (ordered steps + dependencies)                         | none                                    | gpt-5-mini |
| 10  | Lesson Planner             | Compilation   | Sets learning goals, preconditions and postconditions for one step                        | Roadmap step → `LessonPlan`                                                       | none                                    | gpt-5-nano |
| 11  | Lesson Writer              | Compilation   | Writes the lesson content in the user's stack and tone                                    | `LessonPlan` → lesson markdown with citations                                     | `FileSearchTool`                        | gpt-5-mini |
| 12  | Interactive Converter      | Compilation   | Turns the lesson into an interactive page: code blocks, expandable sections, a short quiz | Lesson markdown → HTML page                                                       | none                                    | gpt-5-mini |
| 13  | Page Verifier              | Compilation   | Checks the page has every required section, renders, and has no unsafe script             | HTML → pass/fail + fix list                                                       | `validate_html` (Python)                | gpt-5-nano |


The "Testing team" in the team notes is covered by the Verifier and by our own test runs; it does not need its own agents. Model names are a starting point; we will tune them for cost after the first full run.

## Architecture and agent patterns

All four Lesson 5 patterns appear, each where it fits the work rather than for its own sake.

[embedded content: Pathwise architecture · 13 agents, 4 patterns, 2 stores

Intake hands off to Research for a new topic or to the Tutor for a lesson question. The Research Manager keeps control and calls workers as tools, with search and summaries run in parallel. Sources go to the vector store, which grounds both the Lesson Writer and the Tutor; each roadmap step then runs through the fixed four-step lesson pipeline.

## How Pathwise meets each course requirement

Every component on the Project 1 schedule has a natural place in Pathwise; none is added only to tick a box.


| Requirement                | How Pathwise uses it                                                                                                                                        | Schedule day |
| -------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------ |
| Multiple specialist agents | 13 agents in four teams (see Agent roles)                                                                                                                   | W1 Day 4     |
| Deterministic workflow     | Lesson pipeline: Planner → Writer → Converter → Verifier, in fixed order in code                                                                            | W1 Day 5     |
| Agents as tools            | Research Manager calls Topic Planner, Search, Judge, Summarizer and Critic as tools and keeps control                                                       | W1 Day 5     |
| Handoffs and routing       | Intake Agent hands off to the Research flow (new topic) or the Tutor (question about an existing lesson)                                                    | W1 Day 5     |
| Parallel agents            | One Web Search Agent per query, then one Summarizer per kept article, run with `asyncio.gather`; lessons for independent roadmap steps also run in parallel | W1 Day 5     |
| Input guardrails           | Intake rejects requests that are not about learning a technology, and flags prompt-injection attempts                                                       | W1 Day 4     |
| Output guardrails          | Lesson Writer must cite at least one stored source; Verifier blocks pages with missing sections or unsafe script                                            | W1 Day 4     |
| Short-term memory          | Agents SDK session per chat (`SQLiteSession`); older turns compressed into a running summary                                                                | W2 Days 1–2  |
| Long-term memory           | User profile (level, stack, format, tone) and learning history, loaded into context at the start of each run                                                | W2 Days 1–2  |
| Vector store and RAG       | Kept articles and summaries uploaded to an OpenAI vector store per topic; Lesson Writer and Tutor use `FileSearchTool`                                      | W2 Days 1–2  |
| Database                   | SQLite: users, preferences, chats, roadmaps, lessons, sources, lesson progress                                                                              | W2 Days 1–2  |
| Gradio UI                  | Chat tab, Roadmap tab, Lesson viewer (HTML rendered in `gr.HTML`), My Topics tab                                                                            | W2 Days 1–2  |
| Context engineering        | Each agent receives only the typed object it needs (summaries, not raw pages); user profile passed through the run context                                  | W2 Days 1–2  |
| Tracing                    | Every run wrapped in `trace("Pathwise: <topic>")` for debugging and the demo                                                                                | Throughout   |


**Cost controls** (goal 5): at most 6 search queries and 10 kept articles per topic, one Critic loop at most, nano models for judging and summarising, and research reused when the same topic was already researched.

## Review notes and open questions

The idea is strong and fits the brief well; the main risks are the UI choice and scope.

**Risks and scope decisions**

1. **React vs Gradio.** The team notes say "full UI, web-app — React", but the schedule asks for a Gradio UI in Week 2. Building React plus a backend API in two days, with a midterm the same week, is a real risk. Proposal: Gradio is the required UI and renders lessons as HTML; a React export is a stretch goal.
2. **Agent count.** The team notes list about 16 roles. Thirteen is still a lot for two weeks. The minimum demo (MVP) needs agents 1, 3–5, 7, 9, 10, 11 and 12; the Judge, Critic, Tutor and Verifier are added once the main flow works.
3. **"JEV" in the notes.** We read this as the Relevance Judge (an LLM scoring each search result against the topic). The team should confirm.
4. **"Assessment" in the notes.** This could mean assessing sources (now the Judge) or assessing the learner (a quiz). We put a short quiz inside each lesson page; a separate Quiz Agent can come later.
5. **Web content is untrusted.** Pages returned by search can contain hidden instructions. Summaries treat page text as data only, and the Writer works from stored summaries, not raw pages.
6. **Latency and cost.** A full run (search → summaries → roadmap → several lessons) can take minutes. We generate the roadmap first and write each lesson only when the user opens it.

**Questions for the professor**

- [ ] Is Gradio required, or is a React front end acceptable if the agent backend is the focus?
- [ ] Is `WebSearchTool` (paid per call) acceptable for the demo, or should we use a fixed set of preloaded articles?
- [ ] One vector store per topic, or one shared store with metadata filtering?
- [ ] How will the project be graded: by the number of patterns used, by the quality of the demo, or both?



## Build roadmap

Each day adds one layer on top of a version that already runs end to end.

1. **W1 Day 3 — Plan.** Agree on this proposal and get professor sign-off. Set up the repo: uv project, `.env`, folders `agents/`, `tools/`, `schemas/`, `data/`, `app/`.
2. **W1 Day 4 — Core agents.** Write instructions and Pydantic schemas for the MVP agents. Get a single run working: Intake → Topic Planner → Web Search → Summarizer → Roadmap, printed in a notebook. Add the input guardrail on Intake.
3. **W1 Day 5 — Patterns.** Research Manager calling workers as tools; parallel search and summarise with `asyncio.gather`; Intake handoffs to Research or Tutor; the deterministic lesson pipeline.
4. **Weekend — Refine.** Add the Relevance Judge, Critic loop and Verifier. Tune prompts using traces. Add cost limits.
5. **W2 Days 1–2 — Advanced components.** SQLite database, sessions and user profile memory, vector store upload and `FileSearchTool` for Writer and Tutor, Gradio UI.
6. **W2 Days 3–4 — Midterm.** Feature freeze; only bug fixes.
7. **W2 Day 5 — Wrap up.** End-to-end testing on three sample topics, slides, recorded backup demo.
8. **W2 Day 6 — Present.** Live demo: "Teach me Kafka for Spring Boot" from prompt to interactive lesson, plus a trace walkthrough of the agents.

