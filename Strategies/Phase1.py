from math import ceil, floor

from datamodel import Order, OrderDepth, TradingState
from typing import List
from collections import deque
import jsonpickle

import json
import math
from typing import Any, Dict, List, Optional

try:
    from prosperity3bt.datamodel import (
        Listing,
        Observation,
        Order,
        OrderDepth,
        ProsperityEncoder,
        Symbol,
        Trade,
        TradingState,
    )
except ModuleNotFoundError:
    from datamodel import (
        Listing,
        Observation,
        Order,
        OrderDepth,
        ProsperityEncoder,
        Symbol,
        Trade,
        TradingState,
    )


class Logger:
    """Visualizer-compatible logger kept inside trader.py for submission use."""

    def __init__(self) -> None:
        self.logs = ""
        self.max_log_length = 3750

    def print(self, *objects: Any, sep: str = " ", end: str = "\n") -> None:
        """Collect one human-readable log line for the current backtest tick."""
        self.logs += sep.join(map(str, objects)) + end

    def flush(
        self,
        state: TradingState,
        orders: dict[Symbol, list[Order]],
        conversions: int,
        trader_data: str,
    ) -> None:
        """Emit a single compact JSON payload that the backtester can persist."""
        base_length = len(
            self.to_json(
                [
                    self.compress_state(state, ""),
                    self.compress_orders(orders),
                    conversions,
                    "",
                    "",
                ]
            )
        )

        max_item_length = (self.max_log_length - base_length) // 3

        print(
            self.to_json(
                [
                    self.compress_state(state, self.truncate(state.traderData, max_item_length)),
                    self.compress_orders(orders),
                    conversions,
                    self.truncate(trader_data, max_item_length),
                    self.truncate(self.logs, max_item_length),
                ]
            )
        )

        self.logs = ""

    def compress_state(self, state: TradingState, trader_data: str) -> list[Any]:
        """Mirror the Prosperity log schema used by the visualizer parser."""
        return [
            state.timestamp,
            trader_data,
            self.compress_listings(state.listings),
            self.compress_order_depths(state.order_depths),
            self.compress_trades(state.own_trades),
            self.compress_trades(state.market_trades),
            state.position,
            self.compress_observations(state.observations),
        ]

    def compress_listings(self, listings: dict[Symbol, Listing]) -> list[list[Any]]:
        """Flatten listings into the `[symbol, product, denomination]` tuple layout."""
        return [[listing.symbol, listing.product, listing.denomination] for listing in listings.values()]

    def compress_order_depths(self, order_depths: dict[Symbol, OrderDepth]) -> dict[Symbol, list[Any]]:
        """Serialize the visible book on each symbol as buy/sell price maps."""
        return {
            symbol: [order_depth.buy_orders, order_depth.sell_orders]
            for symbol, order_depth in order_depths.items()
        }

    def compress_trades(self, trades: dict[Symbol, list[Trade]]) -> list[list[Any]]:
        """Flatten trade history so every trade ends up in the same timestamp row."""
        compressed: list[list[Any]] = []
        for trade_list in trades.values():
            for trade in trade_list:
                compressed.append(
                    [
                        trade.symbol,
                        trade.price,
                        trade.quantity,
                        trade.buyer,
                        trade.seller,
                        trade.timestamp,
                    ]
                )
        return compressed

    def compress_observations(self, observations: Observation) -> list[Any]:
        """Pack conversion and plain-value observations into the expected row shape."""
        conversion_observations = {}
        for product, observation in observations.conversionObservations.items():
            conversion_observations[product] = [
                observation.bidPrice,
                observation.askPrice,
                observation.transportFees,
                observation.exportTariff,
                observation.importTariff,
            ]

        return [observations.plainValueObservations, conversion_observations]

    def compress_orders(self, orders: dict[Symbol, list[Order]]) -> list[list[Any]]:
        """Flatten the order batches so they are easy to parse back from JSON."""
        compressed: list[list[Any]] = []
        for order_list in orders.values():
            for order in order_list:
                compressed.append([order.symbol, order.price, order.quantity])
        return compressed

    def to_json(self, value: Any) -> str:
        """Encode Prosperity datatypes into compact JSON without extra spaces."""
        return json.dumps(value, cls=ProsperityEncoder, separators=(",", ":"))

    def truncate(self, value: str, max_length: int) -> str:
        """Shorten long strings while keeping the final JSON payload valid."""
        lo, hi = 0, min(len(value), max_length)
        out = ""

        while lo <= hi:
            mid = (lo + hi) // 2
            candidate = value[:mid]
            if len(candidate) < len(value):
                candidate += "..."

            if len(json.dumps(candidate)) <= max_length:
                out = candidate
                lo = mid + 1
            else:
                hi = mid - 1

        return out


logger = Logger()


def format_plot_payload(*, namespace: Optional[str] = None, **fields: Any) -> str:
    """Format structured logger metadata for the analysis visualizer.

    Use bare `PLOT:` for fields that should appear in the main tooltip.
    Use `PLOT[module]:` when you want the visualizer to render a separate
    module chart below the main plot later on.
    """
    # Keep the payload human-editable so traders can add fields without touching
    # the visualizer code as long as they stick to simple `key=value` pairs.
    parts: List[str] = []
    for key, value in fields.items():
        if isinstance(value, float):
            formatted_value = f"{value:.4f}".rstrip("0").rstrip(".")
        elif isinstance(value, bool):
            formatted_value = "true" if value else "false"
        else:
            formatted_value = str(value)
        parts.append(f"{key}={formatted_value}")

    prefix = "PLOT:" if namespace is None else f"PLOT[{namespace}]:"
    return f"{prefix} " + ", ".join(parts)

invetory_levels = range(-80, 81)

bid_reservation = [
    10.1, 10.1, 10.1, 10.0, 10.0, 10.0, 10.0, 9.9, 9.9, 9.9,
    9.9, 9.8, 9.8, 9.8, 9.8, 9.7, 9.7, 9.7, 9.7, 9.7,
    9.6, 9.6, 9.6, 9.6, 9.5, 9.5, 9.5, 9.5, 9.5, 9.4,
    9.4, 9.4, 9.4, 9.3, 9.3, 9.3, 9.3, 9.3, 9.2, 9.2,
    9.2, 9.2, 9.1, 9.1, 9.1, 9.1, 9.1, 9.0, 9.0, 9.0,
    9.0, 8.9, 8.9, 8.9, 8.9, 8.8, 8.8, 8.8, 8.8, 8.8,
    8.7, 8.7, 8.7, 8.7, 8.6, 8.6, 8.6, 8.6, 8.5, 8.5,
    8.5, 8.5, 8.4, 8.4, 8.4, 8.4, 8.3, 8.3, 8.3, 8.3,
    8.3, 8.2, 8.2, 8.2, 8.2, 8.1, 8.1, 8.1, 8.1, 8.0,
    8.0, 8.0, 8.0, 7.9, 7.9, 7.9, 7.9, 7.8, 7.8, 7.8,
    7.8, 7.7, 7.7, 7.7, 7.7, 7.6, 7.6, 7.6, 7.6, 7.5,
    7.5, 7.5, 7.4, 7.4, 7.4, 7.4, 7.3, 7.3, 7.3, 7.3,
    7.2, 7.2, 7.2, 7.2, 7.1, 7.1, 7.1, 7.1, 7.0, 7.0,
    7.0, 6.9, 6.8, 6.8, 6.7, 6.6, 6.6, 6.5, 6.4, 6.4,
    6.3, 6.2, 6.2, 6.1, 6.0, 5.8, 5.3, 4.8, 4.3, 3.8,
    3.3, 2.6, 2.0, 1.2, 0.7, 0.2, -0.1, -0.5, -0.6, -0.8,
    0.0,
]
ask_reservation = [
    0.0, 10.2, 10.2, 10.2, 10.2, 10.1, 10.1, 10.1, 10.1, 10.0,
    10.0, 10.0, 9.9, 9.9, 9.9, 9.9, 9.8, 9.8, 9.8, 9.8,
    9.8, 9.7, 9.7, 9.7, 9.7, 9.6, 9.6, 9.6, 9.6, 9.6,
    9.5, 9.5, 9.5, 9.5, 9.4, 9.4, 9.4, 9.4, 9.4, 9.3,
    9.3, 9.3, 9.3, 9.2, 9.2, 9.2, 9.2, 9.2, 9.1, 9.1,
    9.1, 9.1, 9.0, 9.0, 9.0, 9.0, 9.0, 8.9, 8.9, 8.9,
    8.9, 8.8, 8.8, 8.8, 8.8, 8.7, 8.7, 8.7, 8.7, 8.6,
    8.6, 8.6, 8.6, 8.6, 8.5, 8.5, 8.5, 8.5, 8.4, 8.4,
    8.4, 8.4, 8.3, 8.3, 8.3, 8.3, 8.2, 8.2, 8.2, 8.2,
    8.1, 8.1, 8.1, 8.1, 8.1, 8.0, 8.0, 8.0, 8.0, 7.9,
    7.9, 7.9, 7.9, 7.8, 7.8, 7.8, 7.7, 7.7, 7.7, 7.7,
    7.6, 7.6, 7.6, 7.6, 7.5, 7.5, 7.5, 7.5, 7.4, 7.4,
    7.4, 7.4, 7.3, 7.3, 7.3, 7.3, 7.2, 7.2, 7.2, 7.1,
    7.1, 7.1, 7.1, 7.1, 7.0, 7.0, 6.9, 6.9, 6.8, 6.7,
    6.7, 6.6, 6.6, 6.5, 6.3, 6.2, 6.3, 6.4, 6.3, 6.1,
    5.9, 5.5, 5.1, 4.7, 4.2, 3.6, 3.0, 2.3, 1.6, 0.9,
    0.3,
]

class Trader:
    MAX_POSITION = 80
    # This gamma determines how much we adjust our reservation price based on our current position.
    # 1600 means that at max position (80), we will adjust our reservation price by 1600/80 = 20 ticks
    OSMIUM_GAMMA = 1/12
    OSMIUM_FV = 10_000
    # OSMIUM_MAX_HALF_SPREAD = 6
    OSMIUM_MAX_HALF_SPREAD = 98

    PEPPER_FV_SLOPE = 0.001
    # no evidance if this insane spread also works the same way as for osmium, but do it anyway because the risk is worth it
    # PEPPER_MAX_HALF_SPREAD = 6
    PEPPER_MAX_HALF_SPREAD = 98

    def __init__(self):
        self.pepper_start_fv = None
        self.last_osmium_mid = 10_000

    def bid(self):
        return -10000000

    def encode_trader_data(self, state: TradingState):
        trader_data = {
            "pepper_start_fv": self.pepper_start_fv,
            "last_osmium_mid": self.last_osmium_mid

        }
        return jsonpickle.encode(trader_data)

    def decode_trader_data(self, trader_data_str: str):
        if trader_data_str:
            trader_data = jsonpickle.decode(trader_data_str)
            self.pepper_start_fv = trader_data.get("pepper_start_fv", None)
            self.last_osmium_mid = trader_data.get("last_osmium_mid", None)
        else:
            self.pepper_start_fv = None
            self.last_osmium_mid = None

    def wall_mid(self, order_depth: OrderDepth, default_mid=None, default_half_spread=8, strict=False):
        """Will find the quotes with the largest quantity on both sides and return the mid."""
        bids = order_depth.buy_orders
        asks = order_depth.sell_orders
        if not bids and not asks:
            return default_mid
        best_bid_price = max(bids, key=lambda price: bids[price]) if bids else None
        best_ask_price = min(asks, key=lambda price: asks[price]) if asks else None
        if best_bid_price is not None and best_ask_price is not None:
            return (best_bid_price + best_ask_price) / 2
        elif strict:
            return default_mid
        elif best_bid_price is not None:
            return best_bid_price + default_half_spread
        elif best_ask_price is not None:
            return best_ask_price - default_half_spread
        else:
            return default_mid

    def best_bid_ask(self, order_depth: OrderDepth):
        bids = order_depth.buy_orders
        asks = order_depth.sell_orders
        best_bid = max(bids.keys()) if bids else None
        best_ask = min(asks.keys()) if asks else None
        return best_bid, best_ask

    def best_bid_ask_qty(self, order_depth: OrderDepth):
        bids = order_depth.buy_orders
        asks = order_depth.sell_orders
        best_bid = max(bids.keys()) if bids else None
        best_ask = min(asks.keys()) if asks else None
        best_bid_qty = bids[best_bid] if best_bid is not None else None
        best_ask_qty = asks[best_ask] if best_ask is not None else None
        return best_bid, best_ask, best_bid_qty, best_ask_qty

    def simulate_fill(self, order_depth: OrderDepth, price: int, quantity: int) -> OrderDepth:
        """Simulate how the order book would look like if we got filled on a given price and quantity."""
        new_buy_orders = order_depth.buy_orders.copy()
        new_sell_orders = order_depth.sell_orders.copy()

        if quantity > 0:
            # Simulate a buy order getting filled, which would reduce the quantity on the sell side
            if price in new_sell_orders:
                new_sell_orders[price] -= quantity
                if new_sell_orders[price] <= 0:
                    del new_sell_orders[price]
        elif quantity < 0:
            # Simulate a sell order getting filled, which would reduce the quantity on the buy side
            if price in new_buy_orders:
                new_buy_orders[price] += quantity  # quantity is negative, so this reduces the buy quantity
                if new_buy_orders[price] <= 0:
                    del new_buy_orders[price]

        od = OrderDepth()
        od.buy_orders = new_buy_orders
        od.sell_orders = new_sell_orders
        return od
    
    def calculate_take_buy_size(self, current_q, market_ask_spread, available_qty, bid_reservations):
        take_qty = 0
        # Evaluate taking unit-by-unit
        for i in range(available_qty):
            simulated_q = current_q + i
            if simulated_q >= 80:
                break
                
            # If the market is offering a price CHEAPER than our required premium
            # Note: Depending on how you orient your signs, make sure this logic matches
            if market_ask_spread <= bid_reservations[simulated_q + 80]:
                take_qty += 1
            else:
                # The moment the next unit isn't profitable, we stop taking
                break 
                
        return take_qty
    
    def calculate_take_sell_size(self, current_q, market_bid_spread, available_qty, ask_reservations):
        take_qty = 0
        # Evaluate taking unit-by-unit
        for i in range(-available_qty):
            simulated_q = current_q - i
            if simulated_q <= -80:
                break
                
            # If the market is offering a price CHEAPER than our required premium
            # Note: Depending on how you orient your signs, make sure this logic matches
            if market_bid_spread >= ask_reservations[simulated_q + 80]:
                take_qty -= 1
            else:
                # The moment the next unit isn't profitable, we stop taking
                break 
                
        return take_qty
    
    def osmium_orders(self, state: TradingState):
        """"
        ASH_COATED_OSMIUM
        we know a two things:
        == It is mean reverting around 10k ==
        Meaning we want to get a larger position when the price is far from 10k, and smaller position when it is close to 10k. 
        For this we can make use of a simple A-S style inventory management, where we adjust our reservation price based on our current position.
        I found that 

        == Our orders will get filled if within 108 ticks from the mid (and we are they only order on that side) ==
        meaning that if we are the only order on the bid side, and we are 108 ticks below the mid, we will get filled.
        we only have to know the mid, which we can estimate using the wall_mid function
        """
        orders: List[Order] = []
        position = state.position.get("ASH_COATED_OSMIUM", 0)
        order_depth = state.order_depths["ASH_COATED_OSMIUM"]
        best_bid, best_ask, bb_qty, ba_qty = self.best_bid_ask_qty(order_depth)

        bid_size = self.MAX_POSITION - position
        ask_size = -self.MAX_POSITION - position

        # A-S style invetory management.
        inventory_adjustment = position * self.OSMIUM_GAMMA
        effective_fv = self.OSMIUM_FV - inventory_adjustment

        # Aggressively trade if best bid/ask is favorable compared to effective fair value
        if best_bid is not None and bb_qty is not None and best_bid > effective_fv + 1 and position > -self.MAX_POSITION:
            size = -bb_qty
            ask_size -= size
            orders.append(Order("ASH_COATED_OSMIUM", best_bid, size))
            order_depth = self.simulate_fill(order_depth, best_bid, size)
            best_bid, best_ask, bb_qty, ba_qty = self.best_bid_ask_qty(order_depth)
        if best_ask is not None and ba_qty is not None and best_ask < effective_fv - 1 and position < self.MAX_POSITION:
            size = -ba_qty
            bid_size -= size
            orders.append(Order("ASH_COATED_OSMIUM", best_ask, size))
            order_depth = self.simulate_fill(order_depth, best_ask, -size)
            best_bid, best_ask, bb_qty, ba_qty = self.best_bid_ask_qty(order_depth)

        total_bid_size, total_ask_size = sum(order_depth.buy_orders.values()), sum(order_depth.sell_orders.values())
        if best_bid is not None and best_ask is not None:
            self.last_osmium_mid = self.wall_mid(order_depth, default_mid=self.last_osmium_mid, strict=True)
        elif best_bid is None or total_bid_size <= 1:
            best_bid = self.last_osmium_mid - self.OSMIUM_MAX_HALF_SPREAD if self.last_osmium_mid is not None else self.OSMIUM_FV - self.OSMIUM_MAX_HALF_SPREAD - 1
        elif best_ask is None or total_ask_size <= 1:
            best_ask = self.last_osmium_mid + self.OSMIUM_MAX_HALF_SPREAD if self.last_osmium_mid is not None else self.OSMIUM_FV + self.OSMIUM_MAX_HALF_SPREAD + 1
        
        # improve the best quote by 1 tick to get in the frot of the queue.
        bid = best_bid + 1 if best_bid is not None else None
        ask = best_ask - 1 if best_ask is not None else None
        bid = ceil(bid) if bid is not None else None
        ask = floor(ask) if ask is not None else None

        # if the best bid/ask is outside of our reservation price, don't place an order, 
        # because we want to be more passive in that case, and wait for the price to come to us.
        if bid is not None and bid > effective_fv:
            bid = self.last_osmium_mid - self.OSMIUM_MAX_HALF_SPREAD if self.last_osmium_mid is not None else self.OSMIUM_FV - self.OSMIUM_MAX_HALF_SPREAD
            bid = ceil(bid)
        if ask is not None and ask < effective_fv:
            ask = self.last_osmium_mid + self.OSMIUM_MAX_HALF_SPREAD if self.last_osmium_mid is not None else self.OSMIUM_FV + self.OSMIUM_MAX_HALF_SPREAD
            ask = floor(ask)

        logger.print(
            f"ASH_COATED_OSMIUM fair={self.OSMIUM_FV:.2f} pos={position} reservation={effective_fv:.2f}",
            f"PLOT: bid={bid}, ask={ask}, fv={self.OSMIUM_FV:.2f}, skew_adj={effective_fv - self.OSMIUM_FV:.2f}",
        )

        if bid is not None and position < self.MAX_POSITION:
            orders.append(Order("ASH_COATED_OSMIUM", bid, bid_size))
        if ask is not None and position > -self.MAX_POSITION:
            orders.append(Order("ASH_COATED_OSMIUM", ask, ask_size))
        return orders

    def pepper_orders(self, state: TradingState):
        orders: List[Order] = []
        position = state.position.get("INTARIAN_PEPPER_ROOT", 0)
        order_depth = state.order_depths["INTARIAN_PEPPER_ROOT"]
        best_bid, best_ask, bb_qty, ba_qty = self.best_bid_ask_qty(order_depth)

        if self.pepper_start_fv is None and (mid := self.wall_mid(order_depth)) is not None:
            self.pepper_start_fv = round(mid / 100) * 100 
        if self.pepper_start_fv is None:
            return []

        fv = self.pepper_start_fv + self.PEPPER_FV_SLOPE * state.timestamp

        idx = int(max(0, min(160, position + 80)))
        
        # 1. NEW TARGET CALCULATION (No magic numbers)
        # Assuming the new DP outputs negative values for bids and positive for asks
        target_bid = floor(fv + bid_reservation[idx]) 
        target_ask = ceil(fv + ask_reservation[idx])

        bid_size = self.MAX_POSITION - position
        ask_size = -self.MAX_POSITION - position
        
        # 2. UNIFIED TAKER LOGIC
        # Aggressively hit the book if it offers better than our thresholds
        
        # If someone is selling (ask) cheaper than our max buy price
        if best_ask is not None and ba_qty is not None and best_ask <= target_bid and position < self.MAX_POSITION:
            size = min(bid_size, -ba_qty)  # ba_qty is negative
            optimal_size = self.calculate_take_buy_size(position, best_ask - fv, -ba_qty, bid_reservation)
            size = min(size, optimal_size)
            if size > 0:
                orders.append(Order("INTARIAN_PEPPER_ROOT", best_ask, size))
                bid_size -= size
                order_depth = self.simulate_fill(order_depth, best_ask, size)
                best_bid, best_ask, bb_qty, ba_qty = self.best_bid_ask_qty(order_depth)

        # If someone is buying (bid) higher than our min sell price
        if best_bid is not None and bb_qty is not None and best_bid >= target_ask and position > -self.MAX_POSITION:
            size = max(ask_size, -bb_qty)  # ask_size and bb_qty (inverted) are negative
            optimal_size = self.calculate_take_sell_size(position, best_bid - fv, -bb_qty, ask_reservation)
            size = max(size, optimal_size)
            if size < 0:
                orders.append(Order("INTARIAN_PEPPER_ROOT", best_bid, size))
                ask_size -= size
                order_depth = self.simulate_fill(order_depth, best_bid, size)
                best_bid, best_ask, bb_qty, ba_qty = self.best_bid_ask_qty(order_depth)
                
        # 3. MAKER QUOTE LOGIC (Remains mostly the same, just respects the new targets)
        quote_bid = best_bid + 1 if best_bid is not None else floor(fv - self.PEPPER_MAX_HALF_SPREAD)
        if bid_size > 0:
            # Ensure we don't cross the current ask (if it exists) or exceed our target
            safe_bid_cap = min(target_bid, best_ask - 1) if best_ask is not None else target_bid
            quote_bid = ceil(min(quote_bid, safe_bid_cap))
            orders.append(Order("INTARIAN_PEPPER_ROOT", quote_bid, bid_size))

        quote_ask = best_ask - 1 if best_ask is not None else ceil(fv + self.PEPPER_MAX_HALF_SPREAD)
        if ask_size < 0:
            # Ensure we don't cross the current bid (if it exists) or exceed our target
            safe_ask_floor = max(target_ask, best_bid + 1) if best_bid is not None else target_ask
            quote_ask = floor(max(quote_ask, safe_ask_floor))
            orders.append(Order("INTARIAN_PEPPER_ROOT", quote_ask, ask_size))

        logger.print(
            f"INTARIAN_PEPPER_ROOT fair={fv:.2f} pos={position} reservation=0.00",
            f"PLOT: bid={quote_bid}, ask={quote_ask}, fv={fv:.2f}, skew_adj=0.0",
        )
        return orders

    def run(self, state: TradingState):
        self.decode_trader_data(state.traderData)

        orders = {}
        for product in state.order_depths:
            if product == "INTARIAN_PEPPER_ROOT":
                orders[product] = self.pepper_orders(state)
            if product == "ASH_COATED_OSMIUM":
                orders[product] = self.osmium_orders(state)

        traderData = self.encode_trader_data(state)
        conversions = 0
        logger.flush(state, orders, conversions, traderData)
        return orders, conversions, traderData