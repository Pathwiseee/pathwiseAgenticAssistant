# Pathwise FAQ

## What is Pathwise?
Pathwise is a learning assistant for people in tech. You tell it what you want to learn,
for example "Kafka for my Spring Boot job". It researches the topic on the web, picks the
most useful sources, and builds an interactive lesson for you. After that you can ask a
tutor follow-up questions about the lesson.

## How do I start learning a new topic?
Type a topic in "Topic for a new chat", click "+ New chat", then describe what you want
to learn: the topic, your level (beginner, intermediate or advanced), your tech stack and
your goal. The more detail you give, the better the lesson fits you.

## How long does it take to build a lesson?
Usually a few minutes. Research takes about 2 minutes, and writing and checking the lesson
takes a few more. You can watch the progress messages in the chat while it works.

## How does Pathwise build a lesson?
Several AI agents work in order. An intake agent understands your request. Research agents
plan web searches, search, score each result, summarize the good sources and list what is
still missing. Compilation agents then plan the lesson, review the plan, write the lesson
and verify it before you see it.

## Where do the lesson's sources come from?
From public web pages found during research, such as official documentation and well-known
engineering blogs. Each source is scored for relevance to your level and tech stack, and
low-quality pages (ads, unrelated pages) are dropped.

## What can I ask the tutor?
Questions about the lesson you just studied: explain a concept again, give an example,
or quiz you. The tutor answers from the lesson and its sources, and shows which sources
it used.

## Why does the tutor say something is not covered?
Research lists subtopics that none of the sources covered ("known gaps"). When you ask
about one of them, the tutor tells you honestly that the lesson's sources don't cover it,
instead of making up an answer.

## Why was my message blocked?
Pathwise only accepts requests about learning technology, programming and related
concepts. Messages that are off-topic, unsafe, or try to change how the assistant works
are blocked with a short explanation.

## Can I learn several topics?
Yes. Each chat holds one lesson. Start a new chat for each new topic. Your chats and
lessons are listed in the sidebar.

## Are my chats saved?
Yes. Chats and lessons are saved in a local database file on the computer running
Pathwise, so you can reopen them later from the sidebar.

## Is my data sent anywhere?
Your messages and the lesson content are sent to OpenAI's API so the AI agents can
process them. The chats and lessons themselves are stored locally.

## What are Pathwise's limits?
- It cannot ask you clarifying questions yet; a vague request goes straight to research.
- Each chat contains one lesson.
- Lessons are only as good as the public sources found online; some advanced subtopics
  may be listed as gaps.