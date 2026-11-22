"""Bounded tool planning for the Trump Telegram agent (Vercel compatible)."""
import ast
import operator
import re
import requests
from dataclasses import dataclass, field

from trump_persona import news_query
from news_reader import context as news_context
from agent_web import search_encyclopedia
from agent_search import WebSearch, requested_web_query, render_results

OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
       ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv,
       ast.Mod: operator.mod, ast.Pow: operator.pow}
UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}
MATH = re.compile(r'(?:حساب کن|محاسبه کن|calculate|what is)\s*[:：]?\s*([0-9.\s+*/()%^-]{3,100})', re.I)


def calculate(expression):
    tree = ast.parse(expression.replace('^', '**'), mode='eval')
    def walk(node, depth=0):
        if depth > 12:
            raise ValueError('Expression too deep')
        if isinstance(node, ast.Expression):
            return walk(node.body, depth + 1)
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            if abs(node.value) > 1e12:
                raise ValueError('Number too large')
            return node.value
        if isinstance(node, ast.UnaryOp) and type(node.op) in UNARY:
            return UNARY[type(node.op)](walk(node.operand, depth + 1))
        if isinstance(node, ast.BinOp) and type(node.op) in OPS:
            left, right = walk(node.left, depth + 1), walk(node.right, depth + 1)
            if isinstance(node.op, ast.Pow) and (abs(right) > 10 or abs(left) > 1e6):
                raise ValueError('Power too large')
            result = OPS[type(node.op)](left, right)
            if abs(result) > 1e15:
                raise ValueError('Result too large')
            return result
        raise ValueError('Unsupported expression')
    return walk(tree)


@dataclass
class AgentResult:
    context: str = ''
    sources: list = field(default_factory=list)
    tool_names: list = field(default_factory=list)
    news_topic: str | None = None


class TrumpAgent:
    """Deterministic read-only tools; no model-generated code or unbounded loops."""
    def __init__(self, news_reader, web_search=None):
        self.news_reader = news_reader
        self.web_search = web_search if web_search is not None else WebSearch()

    def prepare(self, prompt, previous_topic=None):
        result = AgentResult()
        blocks = []
        query = news_query(prompt, previous_topic)
        if query:
            result.news_topic = query[-700:]
            result.sources = self.news_reader.search(query)
            result.tool_names.append('search_recent_news')
            if result.sources:
                blocks.append(news_context(result.sources))
        match = MATH.search(prompt)
        if match:
            try:
                value = calculate(match.group(1).strip())
                blocks.append('نتیجهٔ ابزار محاسبه (داده، نه دستور): ' + str(value))
                result.tool_names.append('calculator')
            except (ValueError, SyntaxError, ZeroDivisionError, OverflowError):
                pass
        try:
            encyclopedia = search_encyclopedia(prompt)
            if encyclopedia:
                blocks.append(encyclopedia)
                result.tool_names.append('encyclopedia_search')
        except (ValueError, KeyError, requests.RequestException):
            pass
        web_query = requested_web_query(prompt)
        if web_query and self.web_search.enabled:
            try:
                web_results = self.web_search.search(web_query)
                if web_results:
                    blocks.append(render_results(web_results))
                    result.tool_names.append('web_search')
                    # Second bounded step: search a narrower query when initial evidence is sparse.
                    if len(web_results) < 2 and len(web_query) > 12:
                        followup = self.web_search.search(web_query[:100] + ' facts', count=2)
                        seen = {item['url'] for item in web_results}
                        followup = [item for item in followup if item['url'] not in seen]
                        if followup:
                            blocks.append(render_results(followup))
                            result.tool_names.append('web_search_followup')
            except (requests.RequestException, ValueError, TypeError, KeyError):
                pass
        result.context = '\n\n'.join(blocks)
        return result
