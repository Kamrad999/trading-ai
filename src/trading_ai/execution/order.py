"""Order class — pure data structure following Zipline/Backtrader patterns.

Order represents intent to trade. No execution logic here.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum


class OrderSide(Enum):
    """Order side."""
    BUY = "buy"
    SELL = "sell"


class OrderStatus(Enum):
    """Order lifecycle status."""
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass
class Order:
    """
    Order — represents trading intent.
    
    Fields:
        symbol: Trading symbol
        side: BUY or SELL
        size: Quantity (positive for buy, negative for sell)
        price: Limit price (None for market orders)
        timestamp: When order was created
        status: Current order status
        filled_price: Actual fill price (set when filled)
        filled_time: When order was filled
    """
    symbol: str
    side: OrderSide
    size: float  # positive = buy/long, negative = sell/short
    timestamp: datetime
    
    # Optional fields
    price: Optional[float] = None  # None = market order
    status: OrderStatus = field(default=OrderStatus.PENDING)
    
    # Fill data (populated when filled)
    filled_price: Optional[float] = None
    filled_time: Optional[datetime] = None
    
    # Internal
    id: str = field(default="")
    
    def __post_init__(self):
        """Generate ID if not provided."""
        if not self.id:
            self.id = f"ord_{self.timestamp.strftime('%Y%m%d_%H%M%S')}_{self.symbol}"
    
    def mark_filled(self, fill_price: float, fill_time: datetime) -> None:
        """Mark order as filled."""
        self.status = OrderStatus.FILLED
        self.filled_price = fill_price
        self.filled_time = fill_time
    
    def mark_cancelled(self) -> None:
        """Mark order as cancelled."""
        self.status = OrderStatus.CANCELLED
    
    @property
    def is_pending(self) -> bool:
        """True if order is pending."""
        return self.status == OrderStatus.PENDING
    
    @property
    def is_filled(self) -> bool:
        """True if order is filled."""
        return self.status == OrderStatus.FILLED
    
    @property
    def is_long(self) -> bool:
        """True if this is a buy order (creates long position)."""
        return self.side == OrderSide.BUY
    
    @property
    def is_short(self) -> bool:
        """True if this is a sell order (creates short position)."""
        return self.side == OrderSide.SELL
