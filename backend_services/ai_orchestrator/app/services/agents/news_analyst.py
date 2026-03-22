"""
News Analyst Agent
Financial news sentiment analysis for monitored assets.
"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import random  # For demo/simulation


@dataclass
class NewsItem:
    """A single news article with sentiment."""
    title: str
    source: str
    sentiment: str  # "positive", "negative", "neutral"
    sentiment_score: float  # -1.0 to 1.0
    relevance: float  # 0.0 to 1.0
    published_at: str
    url: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "source": self.source,
            "sentiment": self.sentiment,
            "sentiment_score": self.sentiment_score,
            "relevance": self.relevance,
            "published_at": self.published_at,
            "url": self.url
        }


@dataclass
class SentimentReport:
    """Aggregated sentiment analysis for a symbol."""
    symbol: str
    overall_sentiment: str
    sentiment_score: float  # Weighted average: -1.0 to 1.0
    news_count: int
    positive_count: int
    negative_count: int
    neutral_count: int
    trending_topics: List[str] = field(default_factory=list)
    top_news: List[NewsItem] = field(default_factory=list)
    alerts: List[str] = field(default_factory=list)
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "overall_sentiment": self.overall_sentiment,
            "sentiment_score": round(self.sentiment_score, 2),
            "news_count": self.news_count,
            "breakdown": {
                "positive": self.positive_count,
                "negative": self.negative_count,
                "neutral": self.neutral_count
            },
            "trending_topics": self.trending_topics,
            "top_news": [n.to_dict() for n in self.top_news[:5]],
            "alerts": self.alerts,
            "timestamp": self.timestamp
        }


class NewsAnalyst:
    """
    The 'Sentiment' Agent (Layer 6).
    Role: News & Social Sentiment Monitor.
    Principle: "I track the pulse of market sentiment for your holdings."
    
    Note: In production, integrate with:
    - Alpha Vantage News API
    - NewsAPI.org
    - Polygon.io
    - Twitter/X API
    """
    
    def __init__(self):
        self.name = "News Analyst"
        self.capabilities = [
            "news_aggregation",
            "sentiment_analysis",
            "trend_detection",
            "alert_generation"
        ]
        
        # Simulated news templates for demo
        self._news_templates = {
            "positive": [
                "{symbol} beats earnings expectations by 15%",
                "Analysts upgrade {symbol} to 'Strong Buy'",
                "{symbol} announces major partnership deal",
                "{symbol} revenue grows 20% year-over-year",
                "Institutional investors increase {symbol} holdings"
            ],
            "negative": [
                "{symbol} misses quarterly revenue targets",
                "{symbol} faces regulatory investigation",
                "Analysts downgrade {symbol} citing concerns",
                "{symbol} CFO announces unexpected departure",
                "{symbol} recalls product due to safety issues"
            ],
            "neutral": [
                "{symbol} reports inline with expectations",
                "{symbol} announces board meeting next week",
                "{symbol} trading volume remains steady",
                "Market watch: {symbol} at key technical levels",
                "{symbol} maintains dividend policy unchanged"
            ]
        }
    
    async def analyze_sentiment(
        self,
        symbols: List[str],
        lookback_days: int = 7
    ) -> Dict[str, SentimentReport]:
        """
        Analyze news sentiment for multiple symbols.
        
        Args:
            symbols: List of stock symbols to analyze
            lookback_days: How many days of news to consider
        
        Returns:
            Dict mapping symbol to SentimentReport
        """
        results = {}
        
        for symbol in symbols:
            report = await self._analyze_single(symbol, lookback_days)
            results[symbol] = report
        
        return results
    
    async def _analyze_single(
        self, 
        symbol: str, 
        lookback_days: int
    ) -> SentimentReport:
        """Analyze sentiment for a single symbol."""
        
        # In production: Fetch real news from API
        # For now: Generate simulated news
        news_items = self._simulate_news(symbol, count=random.randint(5, 15))
        
        if not news_items:
            return SentimentReport(
                symbol=symbol,
                overall_sentiment="neutral",
                sentiment_score=0.0,
                news_count=0,
                positive_count=0,
                negative_count=0,
                neutral_count=0
            )
        
        # Count sentiments
        positive = sum(1 for n in news_items if n.sentiment == "positive")
        negative = sum(1 for n in news_items if n.sentiment == "negative")
        neutral = sum(1 for n in news_items if n.sentiment == "neutral")
        
        # Calculate weighted score
        total_weight = sum(n.relevance for n in news_items)
        if total_weight > 0:
            weighted_score = sum(n.sentiment_score * n.relevance for n in news_items) / total_weight
        else:
            weighted_score = 0.0
        
        # Determine overall sentiment
        if weighted_score > 0.2:
            overall = "positive"
        elif weighted_score < -0.2:
            overall = "negative"
        else:
            overall = "neutral"
        
        # Generate alerts
        alerts = []
        if negative >= 3:
            alerts.append(f"⚠️ Multiple negative news items detected for {symbol}")
        if any(n.sentiment == "negative" and n.relevance > 0.8 for n in news_items):
            alerts.append(f"🚨 High-impact negative news for {symbol}")
        if positive >= 5 and negative == 0:
            alerts.append(f"✅ Strong positive sentiment for {symbol}")
        
        # Sort by relevance for top news
        sorted_news = sorted(news_items, key=lambda x: x.relevance, reverse=True)
        
        return SentimentReport(
            symbol=symbol,
            overall_sentiment=overall,
            sentiment_score=weighted_score,
            news_count=len(news_items),
            positive_count=positive,
            negative_count=negative,
            neutral_count=neutral,
            trending_topics=self._extract_topics(symbol),
            top_news=sorted_news[:5],
            alerts=alerts
        )
    
    def _simulate_news(self, symbol: str, count: int) -> List[NewsItem]:
        """Generate simulated news for demo purposes."""
        news_items = []
        sources = ["Reuters", "Bloomberg", "CNBC", "WSJ", "MarketWatch", "Yahoo Finance"]
        
        for i in range(count):
            # Random sentiment distribution
            rand = random.random()
            if rand < 0.35:
                sentiment = "positive"
                score = random.uniform(0.3, 1.0)
            elif rand < 0.65:
                sentiment = "neutral"
                score = random.uniform(-0.2, 0.2)
            else:
                sentiment = "negative"
                score = random.uniform(-1.0, -0.3)
            
            # Generate title
            template = random.choice(self._news_templates[sentiment])
            title = template.format(symbol=symbol)
            
            # Random time in last 7 days
            hours_ago = random.randint(1, 168)
            pub_time = datetime.now() - timedelta(hours=hours_ago)
            
            news_items.append(NewsItem(
                title=title,
                source=random.choice(sources),
                sentiment=sentiment,
                sentiment_score=score,
                relevance=random.uniform(0.3, 1.0),
                published_at=pub_time.isoformat(),
                url=f"https://example.com/news/{symbol.lower()}/{i}"
            ))
        
        return news_items
    
    def _extract_topics(self, symbol: str) -> List[str]:
        """Extract trending topics (simulated)."""
        all_topics = [
            "earnings", "guidance", "acquisition", "partnership",
            "regulation", "competition", "innovation", "layoffs",
            "expansion", "dividend", "buyback", "lawsuit"
        ]
        return random.sample(all_topics, k=random.randint(2, 4))
    
    async def get_market_mood(self, symbols: List[str]) -> Dict[str, Any]:
        """
        Get overall market mood based on a basket of symbols.
        Useful for dashboard summary.
        """
        reports = await self.analyze_sentiment(symbols)
        
        if not reports:
            return {"mood": "neutral", "score": 0, "symbols_analyzed": 0}
        
        # Aggregate
        total_score = sum(r.sentiment_score for r in reports.values())
        avg_score = total_score / len(reports)
        
        positive_symbols = [s for s, r in reports.items() if r.sentiment_score > 0.2]
        negative_symbols = [s for s, r in reports.items() if r.sentiment_score < -0.2]
        
        if avg_score > 0.3:
            mood = "bullish"
        elif avg_score > 0.1:
            mood = "slightly_bullish"
        elif avg_score < -0.3:
            mood = "bearish"
        elif avg_score < -0.1:
            mood = "slightly_bearish"
        else:
            mood = "neutral"
        
        return {
            "mood": mood,
            "score": round(avg_score, 2),
            "symbols_analyzed": len(reports),
            "positive_symbols": positive_symbols,
            "negative_symbols": negative_symbols,
            "timestamp": datetime.now().isoformat()
        }


# Singleton instance
news_analyst = NewsAnalyst()
