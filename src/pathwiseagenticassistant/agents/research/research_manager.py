import asyncio
from agents import Runner, trace

from pathwiseagenticassistant.agents.research.topic_planning_agent import topic_planning_agent
from pathwiseagenticassistant.agents.research.relevance_judge import relevance_judge_agent, MIN_RELEVANCE_SCORE
from pathwiseagenticassistant.agents.research.critic_agent import critic_agent
from pathwiseagenticassistant.schemas import ResearchPack

MAX_ARTICLES = 6
# ---------- The manager ----------

class ResearchManager:

    def __init__(self, search_agent, summarizer_agent):
        self.search_agent = search_agent
        self.summarizer_agent = summarizer_agent

    async def run(self, request):
        learner = f"topic: {request.topic}, level: {request.level.value}, stack: {request.tech_stack}, goal: {request.goal}"

        with trace("Pathwise research"):

            # STEP 1: plan the searches
            result = await Runner.run(topic_planning_agent, learner)
            plan = result.final_output

            # STEP 2: search the web for all planned queries at the same time (skip duplicate links)

                        
            tasks = [Runner.run(self.search_agent, search.query) for search in plan.searches]
            results = await asyncio.gather(*tasks)

            articles = []
            seen_urls = []
            for result in results:
                for article in result.final_output.results:
                    if article.url not in seen_urls:
                        articles.append(article)
                        seen_urls.append(article.url)

            
            # STEP 3: judge all articles at the same time, keep only the good ones
            tasks = [
                Runner.run(relevance_judge_agent, f"LEARNER: {learner}\nARTICLE: {article.title} | {article.url} | {article.snippet}")
                for article in articles
            ]
            results = await asyncio.gather(*tasks)

            good_articles = []
            for article, result in zip(articles, results):
                if result.final_output.score >= MIN_RELEVANCE_SCORE:
                    good_articles.append(article)
            good_articles = good_articles[:MAX_ARTICLES]

            # STEP 4: summarize each good article
                        # STEP 4: summarize all good articles at the same time
            tasks = [
                Runner.run(self.summarizer_agent, f"title: {article.title}\nurl: {article.url}\nsnippet: {article.snippet}")
                for article in good_articles
            ]
            results = await asyncio.gather(*tasks)

            summaries = []
            for article, result in zip(good_articles, results):
                summary = result.final_output
                summary.title = article.title
                summary.url = article.url
                summaries.append(summary)

            # STEP 5: ask the critic what is missing
            notes = ""
            for s in summaries:
                notes += f"- {s.title}\n  key points: {'; '.join(s.key_points)}\n  covers: {', '.join(s.subtopics_covered)}\n"
            text = f"LEARNER: {learner}\nPLANNED SUBTOPICS: {', '.join(plan.subtopics)}\nARTICLE NOTES:\n{notes}"
            result = await Runner.run(critic_agent, text)
            report = result.final_output

            # STEP 6: pack everything for Compilation
            return ResearchPack(topic=request.topic, summaries=summaries, gaps=report.missing_subtopics)