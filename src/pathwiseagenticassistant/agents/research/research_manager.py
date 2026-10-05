from pydantic import BaseModel
from agents import Runner, trace

from pathwiseagenticassistant.agents.research.topic_planning_agent import topic_planning_agent
from pathwiseagenticassistant.agents.research.relevance_judge import relevance_judge_agent, MIN_RELEVANCE_SCORE
from pathwiseagenticassistant.agents.research.critic_agent import critic_agent
from pathwiseagenticassistant.schemas import ArticleSummary, ResearchPack

MAX_ARTICLES = 6
# ---------- The manager ----------

class ResearchManager:

    def __init__(self, search_agent, summarizer_agent):
        self.search_agent = search_agent
        self.summarizer_agent = summarizer_agent

    async def run(self, request):
        learner = f"topic: {request.topic}, level: {request.user_level}, stack: {request.tech_stack}, goal: {request.goal}"

        with trace("Pathwise research"):

            # STEP 1: plan the searches
            result = await Runner.run(topic_planning_agent, learner)
            plan = result.final_output

            # STEP 2: search the web for each planned query (skip duplicate links)
            articles = []
            seen_urls = []
            for search in plan.searches:
                result = await Runner.run(self.search_agent, search.query)
                for article in result.final_output.articles:
                    if article.url not in seen_urls:
                        articles.append(article)
                        seen_urls.append(article.url)

            # STEP 3: judge each article, keep only the good ones
            good_articles = []
            for article in articles:
                text = f"LEARNER: {learner}\nARTICLE: {article.title} | {article.url} | {article.snippet}"
                result = await Runner.run(relevance_judge_agent, text)
                if result.final_output.score >= MIN_RELEVANCE_SCORE:
                    good_articles.append(article)
            good_articles = good_articles[:MAX_ARTICLES]

            # STEP 4: summarize each good article
            summaries = []
            for article in good_articles:
                text = f"title: {article.title}\nurl: {article.url}\nsnippet: {article.snippet}"
                result = await Runner.run(self.summarizer_agent, text)
                summaries.append(ArticleSummary.model_validate(result.final_output.model_dump()))

            # STEP 5: ask the critic what is missing
            notes = ""
            for s in summaries:
                notes += f"- {s.title}: covers {', '.join(s.subtopics_covered)}\n"
            text = f"LEARNER: {learner}\nPLANNED SUBTOPICS: {', '.join(plan.subtopics)}\nARTICLE NOTES:\n{notes}"
            result = await Runner.run(critic_agent, text)
            report = result.final_output

            # STEP 6: pack everything for the Roadmap Agent
            return ResearchPack(topic=request.topic, summaries=summaries, gaps=report.missing_subtopics)