"""
Risk Analyst Agent
Portfolio risk analysis including VaR, Sharpe Ratio, and concentration risk.
"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import math
from datetime import datetime


@dataclass
class RiskMetrics:
    """Risk metrics for a portfolio or position."""
    var_95: float  # Value at Risk (95% confidence)
    var_99: float  # Value at Risk (99% confidence)
    sharpe_ratio: Optional[float]
    volatility: float
    beta: Optional[float]
    max_drawdown: float
    concentration_risk: str  # "Low", "Medium", "High"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "var_95": round(self.var_95, 2),
            "var_99": round(self.var_99, 2),
            "sharpe_ratio": round(self.sharpe_ratio, 2) if self.sharpe_ratio else None,
            "volatility": round(self.volatility, 4),
            "beta": round(self.beta, 2) if self.beta else None,
            "max_drawdown": round(self.max_drawdown, 4),
            "concentration_risk": self.concentration_risk
        }


@dataclass
class RiskReport:
    """Complete risk analysis report."""
    overall_score: int  # 0-100 (100 = highest risk)
    risk_level: str  # "Low", "Medium", "High", "Critical"
    metrics: RiskMetrics
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_score": self.overall_score,
            "risk_level": self.risk_level,
            "metrics": self.metrics.to_dict(),
            "warnings": self.warnings,
            "recommendations": self.recommendations,
            "timestamp": self.timestamp
        }


class RiskAnalyst:
    """
    The 'Risk' Agent (Layer 5).
    Role: Portfolio Risk Assessment.
    Principle: "I quantify and monitor the risks in your financial positions."
    """
    
    RISK_FREE_RATE = 0.045  # 4.5% annual (current T-Bill rate)
    
    def __init__(self):
        self.name = "Risk Analyst"
        self.capabilities = [
            "var_calculation",
            "sharpe_ratio",
            "concentration_analysis",
            "volatility_measurement"
        ]
    
    def analyze_portfolio(
        self,
        positions: List[Dict[str, Any]],
        historical_returns: Optional[List[float]] = None
    ) -> RiskReport:
        """
        Perform full risk analysis on a portfolio.
        
        Args:
            positions: List of positions with keys: symbol, value, weight, returns
            historical_returns: Optional list of daily/monthly portfolio returns
        """
        warnings = []
        recommendations = []
        
        # Calculate basic metrics
        total_value = sum(p.get("value", 0) for p in positions)
        
        if total_value == 0:
            return RiskReport(
                overall_score=0,
                risk_level="Unknown",
                metrics=RiskMetrics(0, 0, None, 0, None, 0, "Unknown"),
                warnings=["No portfolio value to analyze"]
            )
        
        # 1. Concentration Risk
        concentration = self._analyze_concentration(positions, total_value)
        if concentration["max_weight"] > 0.25:
            warnings.append(f"High concentration: {concentration['top_symbol']} is {concentration['max_weight']*100:.1f}% of portfolio")
            recommendations.append(f"Consider reducing {concentration['top_symbol']} position to below 25%")
        
        # 2. Volatility & VaR
        if historical_returns and len(historical_returns) >= 20:
            volatility = self._calculate_volatility(historical_returns)
            var_95 = self._calculate_var(historical_returns, confidence=0.95)
            var_99 = self._calculate_var(historical_returns, confidence=0.99)
            max_drawdown = self._calculate_max_drawdown(historical_returns)
            sharpe = self._calculate_sharpe(historical_returns, volatility)
        else:
            # Estimate from position data
            avg_return = sum(p.get("expected_return", 0.08) * p.get("weight", 0) for p in positions)
            volatility = sum(p.get("volatility", 0.15) * p.get("weight", 0) for p in positions)
            var_95 = total_value * volatility * 1.645  # Parametric VaR
            var_99 = total_value * volatility * 2.326
            max_drawdown = volatility * 2  # Rough estimate
            sharpe = (avg_return - self.RISK_FREE_RATE) / volatility if volatility > 0 else None
            warnings.append("Limited historical data - using parametric estimates")
        
        # 3. Risk Warnings
        if volatility > 0.25:
            warnings.append("High portfolio volatility detected (>25%)")
            recommendations.append("Consider adding defensive positions or hedges")
        
        if sharpe and sharpe < 0.5:
            warnings.append("Low risk-adjusted returns (Sharpe < 0.5)")
            recommendations.append("Review underperforming positions")
        
        if var_95 > total_value * 0.10:
            warnings.append(f"High VaR: Could lose >${var_95:,.0f} in a bad day (95% conf)")
        
        # 4. Calculate Overall Score
        score = self._calculate_risk_score(
            volatility=volatility,
            var_pct=var_95 / total_value if total_value > 0 else 0,
            concentration=concentration["max_weight"],
            sharpe=sharpe
        )
        
        risk_level = self._score_to_level(score)
        
        metrics = RiskMetrics(
            var_95=var_95,
            var_99=var_99,
            sharpe_ratio=sharpe,
            volatility=volatility,
            beta=None,  # Would need market data
            max_drawdown=max_drawdown,
            concentration_risk=concentration["level"]
        )
        
        return RiskReport(
            overall_score=score,
            risk_level=risk_level,
            metrics=metrics,
            warnings=warnings,
            recommendations=recommendations
        )
    
    def _analyze_concentration(self, positions: List[Dict], total: float) -> Dict[str, Any]:
        """Analyze position concentration."""
        if not positions or total == 0:
            return {"max_weight": 0, "top_symbol": None, "level": "Unknown"}
        
        # Calculate weights
        for p in positions:
            p["weight"] = p.get("value", 0) / total
        
        # Find max
        sorted_pos = sorted(positions, key=lambda x: x.get("weight", 0), reverse=True)
        max_pos = sorted_pos[0]
        max_weight = max_pos.get("weight", 0)
        
        # Determine level
        if max_weight > 0.40:
            level = "High"
        elif max_weight > 0.25:
            level = "Medium"
        else:
            level = "Low"
        
        return {
            "max_weight": max_weight,
            "top_symbol": max_pos.get("symbol", "Unknown"),
            "level": level,
            "top_5": sorted_pos[:5]
        }
    
    def _calculate_volatility(self, returns: List[float]) -> float:
        """Calculate annualized volatility from returns."""
        if len(returns) < 2:
            return 0.0
        
        mean = sum(returns) / len(returns)
        variance = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
        std_dev = math.sqrt(variance)
        
        # Annualize (assuming daily returns)
        return std_dev * math.sqrt(252)
    
    def _calculate_var(self, returns: List[float], confidence: float = 0.95) -> float:
        """Calculate historical Value at Risk."""
        if not returns:
            return 0.0
        
        sorted_returns = sorted(returns)
        index = int((1 - confidence) * len(sorted_returns))
        return abs(sorted_returns[index]) if index < len(sorted_returns) else 0.0
    
    def _calculate_max_drawdown(self, returns: List[float]) -> float:
        """Calculate maximum drawdown from returns."""
        if not returns:
            return 0.0
        
        # Convert returns to cumulative
        cumulative = []
        cum = 1.0
        for r in returns:
            cum *= (1 + r)
            cumulative.append(cum)
        
        # Find max drawdown
        peak = cumulative[0]
        max_dd = 0.0
        
        for value in cumulative:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak
            if drawdown > max_dd:
                max_dd = drawdown
        
        return max_dd
    
    def _calculate_sharpe(self, returns: List[float], volatility: float) -> Optional[float]:
        """Calculate Sharpe Ratio."""
        if not returns or volatility == 0:
            return None
        
        mean_return = sum(returns) / len(returns)
        annualized_return = mean_return * 252  # Assuming daily
        
        return (annualized_return - self.RISK_FREE_RATE) / volatility
    
    def _calculate_risk_score(
        self,
        volatility: float,
        var_pct: float,
        concentration: float,
        sharpe: Optional[float]
    ) -> int:
        """Calculate overall risk score (0-100)."""
        score = 0
        
        # Volatility component (0-30)
        if volatility > 0.40:
            score += 30
        elif volatility > 0.25:
            score += 20
        elif volatility > 0.15:
            score += 10
        
        # VaR component (0-25)
        if var_pct > 0.15:
            score += 25
        elif var_pct > 0.10:
            score += 15
        elif var_pct > 0.05:
            score += 10
        
        # Concentration component (0-25)
        if concentration > 0.50:
            score += 25
        elif concentration > 0.30:
            score += 15
        elif concentration > 0.20:
            score += 10
        
        # Sharpe component (0-20) - poor risk-adjusted returns = more risk
        if sharpe is not None:
            if sharpe < 0:
                score += 20
            elif sharpe < 0.5:
                score += 15
            elif sharpe < 1.0:
                score += 5
        else:
            score += 10  # Unknown
        
        return min(100, max(0, score))
    
    def _score_to_level(self, score: int) -> str:
        """Convert score to risk level."""
        if score >= 75:
            return "Critical"
        elif score >= 50:
            return "High"
        elif score >= 25:
            return "Medium"
        else:
            return "Low"


# Singleton instance
risk_analyst = RiskAnalyst()
