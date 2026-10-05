# Pathwise --- Research Progress

## Overview

I am responsible for the **Research** part of Pathwise. The Research
subsystem takes a `LearningRequest` from the Intake/front-door part of
the application and turns it into a `ResearchPack` for the
Compilation/Roadmap part.

## What I Have Implemented

### 1. Topic Planning

Implemented the Topic Planning Agent to:

-   Generate **4--8 subtopics** in learning order.
-   Generate **5 search items** based on fixed research angles:
    -   `what_it_is`
    -   `problem_it_solves`
    -   `pros_and_cons`
    -   `real_world_example`
    -   `how_to`
-   Make the `how_to` search consider the learner's technology stack.

### 2. Relevance Judge

Implemented an LLM-based relevance judge that:

-   Scores each article from **1--5**.
-   Provides a short reason for the score.
-   Uses a typed/Pydantic output.
-   Uses a code-level threshold of **3** to decide whether an article is
    kept.

This was tested with Kafka-related results, including the **Franz Kafka
vs. Apache Kafka** ambiguity.

### 3. Research Critic

Implemented a Critic Agent that reviews the collected research and
identifies:

-   Missing subtopics
-   Contradictions
-   Follow-up search queries

A test with **Consumer Groups** intentionally omitted showed that the
Critic could identify the missing topic and generate a follow-up query.

### 4. Research Manager

Implemented a Python `ResearchManager` that orchestrates the research
workflow in a fixed order:

``` text
LearningRequest
    ↓
Topic Planning
    ↓
Search
    ↓
Relevance Judge
    ↓
Summarization
    ↓
Critic
    ↓
ResearchPack
```

The manager uses **dependency injection** for the search and summarizer
components, which allowed the research workflow to be tested with
temporary stand-ins while the teammate implementations were still in
progress.

## Testing

The research components were tested end-to-end using a Kafka learning
request with:

-   Intermediate learner level
-   Java / Spring Boot stack
-   Microservices goal

The Research Manager successfully produced a `ResearchPack` using the
temporary search and summarizer components.

## Current Next Steps

-   Integrate John's real Web Search and Summarizer components.
-   Parallelize independent searches.
-   Add the planned bounded gap-fill round using the Critic's follow-up
    queries.
-   Confirm/finalize the `ResearchPack` contract with the
    Compilation/Roadmap component.
-   Continue integration testing with the complete Pathwise system.
