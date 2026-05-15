from dataclasses import dataclass
from typing import List, Optional

try:
    from prosperity3bt.datamodel import Listing, Observation, Order, OrderDepth, ProsperityEncoder, Symbol, Trade, TradingState
except ModuleNotFoundError:
    from datamodel import Listing, Observation, Order, OrderDepth, ProsperityEncoder, Symbol, Trade, TradingState

import json
import math

POS_LIMIT = 10
LONG, NEUTRAL, SHORT = 1, 0, -1
MAX_HISTORY = 170
MM_V12_SKEW_PER_UNIT = 0.4
MM_V12_HARD_PULL = 8
MM_V12_QUOTE_SIZE = 5
MM_V12_WALL_VOL_THRESH = 15

# ── Asset universe ───────────────────────────────────────────────────────────
# - **Galaxy Sounds Recorders**: `GALAXY_SOUNDS_DARK_MATTER`, `GALAXY_SOUNDS_BLACK_HOLES`, `GALAXY_SOUNDS_PLANETARY_RINGS`, `GALAXY_SOUNDS_SOLAR_WINDS`, `GALAXY_SOUNDS_SOLAR_FLAMES`
# - **Vertical Sleeping Pods**: `SLEEP_POD_SUEDE`, `SLEEP_POD_LAMB_WOOL`, `SLEEP_POD_POLYESTER`, `SLEEP_POD_NYLON`, `SLEEP_POD_COTTON`
# - **Organic Microchips**: `MICROCHIP_CIRCLE`, `MICROCHIP_OVAL`, `MICROCHIP_SQUARE`, `MICROCHIP_RECTANGLE`, `MICROCHIP_TRIANGLE`
# - **Purification Pebbles**: `PEBBLES_XS`, `PEBBLES_S`, `PEBBLES_M`, `PEBBLES_L`, `PEBBLES_XL`
# - **Domestic Robots**: `ROBOT_VACUUMING`, `ROBOT_MOPPING`, `ROBOT_DISHES`, `ROBOT_LAUNDRY`, `ROBOT_IRONING`
# - **UV-Visors**: `UV_VISOR_YELLOW`, `UV_VISOR_AMBER`, `UV_VISOR_ORANGE`, `UV_VISOR_RED`, `UV_VISOR_MAGENTA`
# - **Instant Translators**: `TRANSLATOR_SPACE_GRAY`, `TRANSLATOR_ASTRO_BLACK`, `TRANSLATOR_ECLIPSE_CHARCOAL`, `TRANSLATOR_GRAPHITE_MIST`, `TRANSLATOR_VOID_BLUE`
# - **Construction Panels**: `PANEL_1X2`, `PANEL_2X2`, `PANEL_1X4`, `PANEL_2X4`, `PANEL_4X4`
# - **Liquid Breath Oxygen Shakes**: `OXYGEN_SHAKE_MORNING_BREATH`, `OXYGEN_SHAKE_EVENING_BREATH`, `OXYGEN_SHAKE_MINT`, `OXYGEN_SHAKE_CHOCOLATE`, `OXYGEN_SHAKE_GARLIC`
# - **Protein Snack Packs**: `SNACKPACK_CHOCOLATE`, `SNACKPACK_VANILLA` `SNACKPACK_PISTACHIO`, `SNACKPACK_STRAWBERRY`, `SNACKPACK_RASPBERRY`

Z_MR = 0.8
CORRELATIONS: list[dict] = [
    {
        "weights": {
            "MICROCHIP_OVAL": 2,
            "MICROCHIP_RECTANGLE": -2,
            "MICROCHIP_TRIANGLE": -3,
        },
        "mu": -30172,
        "omega": 1044,
        "z": Z_MR,
        "killswitch_omega_factor": 4.0,
    },
    # {
    #     "weights": {
    #         "MICROCHIP_CIRCLE": 1,
    #         "MICROCHIP_RECTANGLE": 2,
    #         "MICROCHIP_SQUARE": 1,
    #         "MICROCHIP_TRIANGLE": 1,
    #     },
    #     "mu": 49944,
    #     "omega": 850,
    #     "z": Z_MR,
    #     "killswitch_omega_factor": 4.0,
    # },
    {
        "weights": {
            "SLEEP_POD_COTTON": 2,
            "SLEEP_POD_LAMB_WOOL": -3,
            "SLEEP_POD_NYLON": 2,
            "SLEEP_POD_POLYESTER": -4,
            "SLEEP_POD_SUEDE": 2,
        },
        "mu": -14421,
        "omega": 1515,
        "z": Z_MR,
        "killswitch_omega_factor": 4.0,
    },
    {
        "weights": {
            "SNACKPACK_CHOCOLATE": 5,
            "SNACKPACK_RASPBERRY": -2,
            "SNACKPACK_STRAWBERRY": 1,
            "SNACKPACK_VANILLA": 5,
        },
        "mu": 90259,
        "omega": 489,
        "z": Z_MR,
        "killswitch_omega_factor": 4.0,
    },
    # {
    #     "weights": {
    #         "SNACKPACK_CHOCOLATE": 2,
    #         "SNACKPACK_PISTACHIO": 1,
    #         "SNACKPACK_STRAWBERRY": 1,
    #         "SNACKPACK_VANILLA": 2,
    #     },
    #     "mu": 60084,
    #     "omega": 274,
    #     "z": Z_MR,
    # },
    {
        "weights": {
            "ROBOT_DISHES": 5,
            "ROBOT_IRONING": 2,
            "ROBOT_LAUNDRY": 2,
            "ROBOT_MOPPING": 4,
            "ROBOT_VACUUMING": 5,
        },
        "mu": 177338,
        "omega": 1832,
        "z": Z_MR,
        "killswitch_omega_factor": 4.0,
    },

]

PEBBLES_PRODUCTS = (
    "PEBBLES_XS",
    "PEBBLES_S",
    "PEBBLES_M",
    "PEBBLES_L",
    "PEBBLES_XL",
)


def get_signal_rule_list(signal_rules: object, signal_name: str) -> list[dict]:
    if not isinstance(signal_rules, dict):
        return []
    raw_rule = signal_rules.get(signal_name)
    if isinstance(raw_rule, dict):
        return [raw_rule]
    if isinstance(raw_rule, list):
        return [rule for rule in raw_rule if isinstance(rule, dict)]
    return []

PEBBLES_ANCHOR = 50_000.0
PEBBLES_CONFIG = {
    "PEBBLES_XS": {
        "enabled": True,
        "target_half_spread": 4.0,
        "own_position_skew": 1.0,
        "default_bearish_bias": 5.0,
        "max_reservation_shift": 6.0,
        "one_sided_position_limit": POS_LIMIT - 2,
        "fallback_half_spread": 6.0,
        "signal_target_position": 6,
        "signal_reservation_shift": 4.0,
        "taker_edge": 10.0,
        "signals": {
            "long": {
                "source": "PEBBLES_XL",
                "lag": 150,
                "threshold": 450.0,
                "hold_ticks": 150,
            },
            "short": [
                {
                    "source": "PEBBLES_L",
                    "lag": 150,
                    "threshold": 230.0,
                    "hold_ticks": 150,
                },
                {
                    "kind": "own_trade_combo",
                    "combo": {
                        "PEBBLES_XS": "B",
                        "PEBBLES_S": ".",
                        "PEBBLES_M": ".",
                        "PEBBLES_L": ".",
                        "PEBBLES_XL": ".",
                    },
                    "hold_ticks": 100,
                    "score_weight": 1.15,
                },
            ],
        },
    },
    "PEBBLES_S": {
        "enabled": True,
        "target_half_spread": 5.0,
        "own_position_skew": 0.75,
        "default_bearish_bias": 0.0,
        "max_reservation_shift": 6.0,
        "one_sided_position_limit": POS_LIMIT - 4,
        "fallback_half_spread": 7.0,
        "signal_target_position": 4,
        "signal_reservation_shift": 4.0,
        "taker_edge": 20.0,
        "signals": {
            "long": {
                "source": "PEBBLES_M",
                "direction": "down",
                "lag": 150,
                "threshold": 434.0,
                "hold_ticks": 150,
            },
            "short": {
                "source": "PEBBLES_XS",
                "direction": "down",
                "lag": 100,
                "threshold": 327.0,
                "hold_ticks": 150,
            },
        },
    },
    "PEBBLES_M": {
        "enabled": False,
        "target_half_spread": 6.0,
        "own_position_skew": 0.75,
        "default_bearish_bias": 0.0,
        "max_reservation_shift": 6.0,
        "one_sided_position_limit": POS_LIMIT - 4,
        "fallback_half_spread": 8.0,
        "signal_target_position": 0,
        "signal_reservation_shift": 0.0,
        "taker_edge": 22.0,
        "signals": {},
    },
    "PEBBLES_L": {
        "enabled": True,
        "target_half_spread": 6.0,
        "own_position_skew": 0.75,
        "default_bearish_bias": 0.0,
        "max_reservation_shift": 6.0,
        "one_sided_position_limit": POS_LIMIT - 4,
        "fallback_half_spread": 8.0,
        "signal_target_position": 0,
        "signal_reservation_shift": 0.0,
        "taker_edge": 22.0,
        "signals": {},
    },
    "PEBBLES_XL": {
        "enabled": True,
        "target_half_spread": 6.0,
        "own_position_skew": 0.75,
        "default_bearish_bias": 0.0,
        "max_reservation_shift": 6.0,
        "one_sided_position_limit": POS_LIMIT - 4,
        "fallback_half_spread": 9.0,
        "signal_target_position": 4,
        "signal_reservation_shift": 6.0,
        "taker_edge": 20.0,
        "signals": {
            "long": {
                "source": "PEBBLES_L",
                "direction": "up",
                "lag": 150,
                "threshold": 230.0,
                "hold_ticks": 150,
                "score_weight": 1.0,
            },
            "short": {
                "source": "PEBBLES_L",
                "direction": "up",
                "lag": 30,
                "threshold": 170.0,
                "hold_ticks": 40,
                "score_weight": 1.35,
            },
        },
    },
}


def get_tracked_history_symbols() -> set[str]:
    tracked_symbols = set()
    for settings in PEBBLES_CONFIG.values():
        if not bool(settings.get("enabled", False)):
            continue
        signal_symbol = settings.get("signal_symbol")
        if isinstance(signal_symbol, str) and signal_symbol:
            tracked_symbols.add(signal_symbol)
        signal_rules = settings.get("signals", {})
        if isinstance(signal_rules, dict):
            for signal_name in ("long", "short"):
                for rule in get_signal_rule_list(signal_rules, signal_name):
                    source_symbol = rule.get("source")
                    if isinstance(source_symbol, str) and source_symbol:
                        tracked_symbols.add(source_symbol)
    return tracked_symbols

@dataclass
class StrategyIntent:
    strategy_name: str
    target_pos: int
    weight: float = 1.0
    max_buy_price: Optional[int] = None
    min_sell_price: Optional[int] = None

class ProductTrader:

    def __init__(self, name, state, prints, new_trader_data, last_trader_data=None):

        self.orders = []

        self.name = name
        self.state = state
        self.prints = prints
        self.new_trader_data = new_trader_data

        self.last_traderData = last_trader_data if isinstance(last_trader_data, dict) else self.get_last_traderData()

        self.initial_position = self.state.position.get(self.name, 0) # position at beginning of round
        self.expected_position = self.initial_position # update this if you expect a certain change in position e.g. to already hedge

        self.mkt_buy_orders, self.mkt_sell_orders = self.get_order_depth()
        self.bid_wall, self.wall_mid, self.ask_wall = self.get_walls()
        self.best_bid, self.best_ask = self.get_best_bid_ask()
        self.update_history()

        self.max_allowed_buy_volume, self.max_allowed_sell_volume = self.get_max_allowed_volume() # gets updated when order created
        self.total_mkt_buy_volume, self.total_mkt_sell_volume = self.get_total_market_buy_sell_volume()

        self.position_locked = False # set to true if you want to prevent any changes in position e.g. when you dont want it to be used as hedge
        self.lock_buy_mm = False
        self.lock_sell_mm = False
        self.intents: List[StrategyIntent] = []

    def get_last_traderData(self):
        last_traderData = {}
        try:
            if self.state.traderData != '':
                last_traderData = json.loads(self.state.traderData)
        except Exception:
            self.log("ERROR", 'td')

        return last_traderData

    def get_history(self):
        if self.name not in get_tracked_history_symbols():
            return []
        history_by_symbol = self.last_traderData.get("price_history", {})
        if not isinstance(history_by_symbol, dict):
            return []
        history = history_by_symbol.get(self.name, [])
        if not isinstance(history, list):
            return []
        return history
    
    def update_history(self):
        if self.name not in get_tracked_history_symbols():
            return
        history = list(self.get_history())
        history.append(self.wall_mid)
        if len(history) > MAX_HISTORY:
            history = history[-MAX_HISTORY:]
        history_by_symbol = self.new_trader_data.setdefault("price_history", {})
        history_by_symbol[self.name] = history

    def get_history_price_value(self, history_entry) -> Optional[float]:
        if isinstance(history_entry, dict):
            value = history_entry.get("wall_mid")
            return float(value) if isinstance(value, (int, float)) else None
        if isinstance(history_entry, (int, float)):
            return float(history_entry)
        return None
    
    def get_price_from_history(self, ticks_ago: int) -> Optional[float]:
        history = self.get_history()
        if ticks_ago <= 0:
            return self.wall_mid
        if len(history) <= ticks_ago:
            return None
        return self.get_history_price_value(history[-(ticks_ago + 1)])

    def get_best_bid_ask(self):
        best_bid = best_ask = None

        try:
            if len(self.mkt_buy_orders) > 0:
                best_bid = max(self.mkt_buy_orders.keys())
            if len(self.mkt_sell_orders) > 0:
                best_ask = min(self.mkt_sell_orders.keys())
        except Exception:
            pass

        return best_bid, best_ask

    def get_reference_price(self):
        _, wall_mid, _ = self.get_walls()
        if wall_mid is not None:
            return wall_mid
        if self.best_bid is not None and self.best_ask is not None:
            return (self.best_bid + self.best_ask) / 2
        if self.best_bid is not None:
            return float(self.best_bid)
        if self.best_ask is not None:
            return float(self.best_ask)
        return self.wall_mid

    def get_walls(self):

        bid_wall = wall_mid = ask_wall = None

        try:
            bid_wall = min([x for x, _ in self.mkt_buy_orders.items()])
        except Exception:
            pass

        try:
            ask_wall = max([x for x, _ in self.mkt_sell_orders.items()])
        except Exception:
            pass

        if bid_wall is not None and ask_wall is not None:
            wall_mid = (bid_wall + ask_wall) / 2

        return bid_wall, wall_mid, ask_wall
    
    def get_total_market_buy_sell_volume(self):
        market_bid_volume = sum([v for _, v in self.mkt_buy_orders.items()])
        market_ask_volume = sum([v for _, v in self.mkt_sell_orders.items()])
        return market_bid_volume, market_ask_volume

    def get_max_allowed_volume(self):
        max_allowed_buy_volume = POS_LIMIT - self.initial_position
        max_allowed_sell_volume = POS_LIMIT + self.initial_position
        return max_allowed_buy_volume, max_allowed_sell_volume

    def get_order_depth(self):
        order_depth = OrderDepth()
        buy_orders = {}
        sell_orders = {}

        try:
            order_depth = self.state.order_depths[self.name]
        except Exception:
            pass
        try:
            buy_orders = {bp: abs(bv) for bp, bv in sorted(order_depth.buy_orders.items(), key=lambda x: x[0], reverse=True)}
        except Exception:
            pass
        try:
            sell_orders = {sp: abs(sv) for sp, sv in sorted(order_depth.sell_orders.items(), key=lambda x: x[0])}
        except Exception:
            pass

        return buy_orders, sell_orders

    def bid(self, price, volume, logging=True):
        abs_volume = min(abs(int(volume)), self.max_allowed_buy_volume)
        if abs_volume <= 0:
            return
        order = Order(self.name, int(price), abs_volume)
        if logging:
            self.log("BUYO", {"p": price, "s": self.name, "v": abs_volume}, product_group='ORDERS')
        self.max_allowed_buy_volume -= abs_volume
        self.expected_position += abs_volume
        self.orders.append(order)

    def ask(self, price, volume, logging=True):
        abs_volume = min(abs(int(volume)), self.max_allowed_sell_volume)
        if abs_volume <= 0:
            return
        order = Order(self.name, int(price), -abs_volume)
        if logging:
            self.log("SELLO", {"p": price, "s": self.name, "v": abs_volume}, product_group='ORDERS')
        self.max_allowed_sell_volume -= abs_volume
        self.expected_position -= abs_volume
        self.orders.append(order)

    def orders_to_reach_target(
        self,
        symbol: str,
        order_depth: OrderDepth,
        current_position: int,
        target: int,
        max_buy_price: Optional[int] = None,
        min_sell_price: Optional[int] = None,
        post_remainder: bool = True,
    ):
        """Generate market-taking orders to move position from current to target."""
        diff = target - current_position
        if diff > 0:
            best_ask = None
            for ask_price in sorted(order_depth.sell_orders.keys()):
                if diff <= 0 or self.max_allowed_buy_volume <= 0:
                    break
                if max_buy_price is not None and ask_price > max_buy_price:
                    continue
                if best_ask is None:
                    best_ask = ask_price
                available = abs(order_depth.sell_orders[ask_price])
                qty = min(diff, available, self.max_allowed_buy_volume)
                if qty > 0:
                    self.bid(ask_price, qty, logging=False)
                    diff -= qty
            # Place limit order for remaining size above best bid
            if post_remainder and diff > 0 and self.max_allowed_buy_volume > 0 and best_ask is not None:
                limit_qty = min(diff, self.max_allowed_buy_volume)
                limit_price = best_ask - 1
                if limit_price > 0:
                    self.bid(limit_price, limit_qty, logging=False)
        elif diff < 0:
            best_bid = None
            for bid_price in sorted(order_depth.buy_orders.keys(), reverse=True):
                if diff >= 0 or self.max_allowed_sell_volume <= 0:
                    break
                if min_sell_price is not None and bid_price < min_sell_price:
                    continue
                if best_bid is None:
                    best_bid = bid_price
                available = abs(order_depth.buy_orders[bid_price])
                qty = min(-diff, available, self.max_allowed_sell_volume)
                if qty > 0:
                    self.ask(bid_price, qty, logging=False)
                    diff += qty
            # Place limit order for remaining size below best ask
            if post_remainder and diff < 0 and self.max_allowed_sell_volume > 0 and best_bid is not None:
                limit_qty = min(-diff, self.max_allowed_sell_volume)
                limit_price = best_bid + 1
                self.ask(limit_price, limit_qty, logging=False)

    def log(self, key, value, product_group=None):
        if product_group is not None:
            if product_group not in self.prints:
                self.prints[product_group] = {}
            self.prints[product_group][key] = value
        else:
            self.prints[key] = value

    def add_intent(self, strategy_name, target_pos, weight=1.0, max_buy_price=None, min_sell_price=None):
        intent = StrategyIntent(strategy_name=strategy_name, target_pos=target_pos, weight=weight, max_buy_price=max_buy_price, min_sell_price=min_sell_price)
        self.intents.append(intent)

    def get_orders(self) -> list[Order]:
        # get the weighted average of the target positions of the intents, and create orders to reach that target position
        if self.position_locked:
            return self.orders
        if len(self.intents) == 0:
            return self.mm_to_the_max()
        total_weight = sum([intent.weight for intent in self.intents])
        if total_weight == 0:
            return self.mm_to_the_max()
        weighted_target_pos = sum([intent.target_pos * intent.weight for intent in self.intents]) / total_weight
        target_pos = int(round(weighted_target_pos))
        target_pos = max(-POS_LIMIT, min(POS_LIMIT, target_pos))
        self.orders_to_reach_target(
            symbol=self.name,
            order_depth=self.state.order_depths.get(self.name, OrderDepth()),
            current_position=self.expected_position,
            target=target_pos,
            max_buy_price=min([intent.max_buy_price for intent in self.intents if intent.max_buy_price is not None], default=None),
            min_sell_price=max([intent.min_sell_price for intent in self.intents if intent.min_sell_price is not None], default=None),
        )
        return self.mm_to_the_max()
    
    def mm_to_the_max(self) -> list[Order]:
        # posts limit orders on both sides with max size
        if self.position_locked:
            return self.orders
        if self.max_allowed_buy_volume > 0 and self.best_bid is not None and not self.lock_buy_mm:
            self.bid(self.best_bid + 1, self.max_allowed_buy_volume, logging=False)
        if self.max_allowed_sell_volume > 0 and self.best_ask is not None and not self.lock_sell_mm:
            self.ask(self.best_ask - 1, self.max_allowed_sell_volume, logging=False)
        return self.orders
    

class EtfTrader:
    def __init__(self, state: TradingState, prints: dict, assets: dict[str, ProductTrader], settings: dict, new_trader_data: dict, last_trader_data: dict):
        self.state = state
        self.prints = prints
        self.assets = assets
        self.new_trader_data = new_trader_data
        self.weights = settings.get("weights", settings.get("factors", {}))
        self.omega = settings.get("omega", 0.0)
        self.mu = settings.get("mu", 0.0)
        self.z = settings.get("z", 1.0)
        self.buy_threshold = self.mu - self.z * self.omega
        self.sell_threshold = self.mu + self.z * self.omega
        # MEAN REVERSION KILLSWITCH
        self.killswitch_omega_factor = float(settings.get("killswitch_omega_factor", 100.0))
        self.killswitch_buy_threshold = self.mu - self.killswitch_omega_factor * self.omega
        self.killswitch_sell_threshold = self.mu + self.killswitch_omega_factor * self.omega
        self.name = settings.get("name", "|".join(sorted(self.weights.keys())))
        self.killswitch_latched = bool(last_trader_data.get("etf_killswitch", {}).get(self.name, False))

    def get_signal_direction(self, basket_price: float) -> int:
        if basket_price >= self.sell_threshold:
            return SHORT
        if basket_price <= self.buy_threshold:
            return LONG
        return NEUTRAL

    def calculate_intents(self):
        basket_price = self.compute_ensemble_price()
        if basket_price is None:
            return

        # MEAN REVERSION KILLSWITCH
        killswitch_active = self.killswitch_latched or basket_price <= self.killswitch_buy_threshold or basket_price >= self.killswitch_sell_threshold
        self.new_trader_data.setdefault("etf_killswitch", {})[self.name] = killswitch_active
        if killswitch_active:
            target_positions = {}
            if not self.killswitch_latched:
                self.killswitch_latched = True
                for asset in self.weights:
                    asset_trader = self.assets.get(asset)
                    if asset_trader is None or asset_trader.position_locked:
                        continue
                    target_positions[asset] = 0
                    asset_trader.add_intent(strategy_name="etf_killswitch:" + self.name, target_pos=0, weight=1.0)
            self.prints.setdefault("ETF", {})[self.name] = {
                "price": round(basket_price, 4),
                "buy_threshold": self.buy_threshold,
                "sell_threshold": self.sell_threshold,
                "killswitch_omega_factor": self.killswitch_omega_factor,
                "killswitch_buy_threshold": self.killswitch_buy_threshold,
                "killswitch_sell_threshold": self.killswitch_sell_threshold,
                "killswitch_active": True,
                "killswitch_latched": True,
                "signal_direction": NEUTRAL,
                "targets": target_positions,
            }
            return

        signal_direction = self.get_signal_direction(basket_price)
        target_positions: dict[str, int] = {}

        if signal_direction == NEUTRAL:
            self.prints.setdefault("ETF", {})[self.name] = {
                "price": round(basket_price, 4),
                "buy_threshold": self.buy_threshold,
                "sell_threshold": self.sell_threshold,
                "killswitch_omega_factor": self.killswitch_omega_factor,
                "killswitch_buy_threshold": self.killswitch_buy_threshold,
                "killswitch_sell_threshold": self.killswitch_sell_threshold,
                "killswitch_active": False,
                "killswitch_latched": False,
                "signal_direction": signal_direction,
                "targets": target_positions,
            }
            return

        for asset, basket_weight in self.weights.items():
            asset_trader = self.assets.get(asset)
            if asset_trader is None or asset_trader.position_locked:
                continue

            target_pos = int(round(signal_direction * float(basket_weight)))
            target_pos = max(-POS_LIMIT, min(POS_LIMIT, target_pos))

            target_positions[asset] = target_pos
            asset_trader.add_intent(
                strategy_name="etf:" + self.name,
                target_pos=target_pos,
                weight=1.0,
            )

        self.prints.setdefault("ETF", {})[self.name] = {
            "price": round(basket_price, 4),
            "buy_threshold": self.buy_threshold,
            "sell_threshold": self.sell_threshold,
            "killswitch_omega_factor": self.killswitch_omega_factor,
            "killswitch_buy_threshold": self.killswitch_buy_threshold,
            "killswitch_sell_threshold": self.killswitch_sell_threshold,
            "killswitch_active": False,
            "killswitch_latched": False,
            "signal_direction": signal_direction,
            "targets": target_positions,
        }

    def compute_ensemble_price(self):
        price = 0.0
        for asset, weight in self.weights.items():
            asset_trader = self.assets.get(asset)
            if asset_trader is None:
                return None
            asset_price = asset_trader.get_reference_price()
            if asset_price is None:
                return None
            price += weight * asset_price
        return price


class JumpTrader:
    ''' Trades the inefficiency that sometimes occurs (Large move Up -> Large move Down -> repeat) '''

    STATE_KEY = "jump"
    TICKS_TO_ACTIVATE = 3
    DISABLE_GRACE_TICKS = 600
    MIN_FIRST_MOVE = 60
    MAX_SMALL_MOVE = 5
    MIN_LARGE_MOVE = 60

    def __init__(self, state: TradingState, prints: dict, assets: dict[str, ProductTrader], new_trader_data: dict):
        self.state = state
        self.prints = prints
        self.assets = assets
        self.new_trader_data = new_trader_data
        self.last_trader_data = self.get_last_trader_data()

    def get_last_trader_data(self) -> dict:
        try:
            trader_data = json.loads(self.state.traderData) if self.state.traderData else {}
        except Exception:
            return {}
        stored = trader_data.get(self.STATE_KEY, {})
        if isinstance(stored, dict):
            return stored
        return {}

    def get_symbol_state(self, symbol: str) -> dict:
        previous = self.last_trader_data.get(symbol, {})
        return {
            "last_wall_mid": previous.get("last_wall_mid"),
            "stable_ticks": int(previous.get("stable_ticks", 0)),
            "move_ticks": int(previous.get("move_ticks", 0)),
            "active": bool(previous.get("active", False)),
            "awaiting_first_move": bool(previous.get("awaiting_first_move", False)),
            "last_move": int(previous.get("last_move", 0)),
            "disable_ticks_waited": max(0, int(previous.get("disable_ticks_waited", 0))),
            "disable_return_mid": previous.get("disable_return_mid"),
        }

    def persist_symbol_state(self, symbol: str, symbol_state: dict) -> None:
        strategy_state = self.new_trader_data.setdefault(self.STATE_KEY, {})
        strategy_state[symbol] = symbol_state

    def target_from_last_move(self, last_move: int) -> Optional[int]:
        if last_move > 0:
            return -POS_LIMIT
        if last_move < 0:
            return POS_LIMIT
        return None

    def clear_pending_disable(self, symbol_state: dict) -> None:
        symbol_state["disable_ticks_waited"] = 0
        symbol_state["disable_return_mid"] = None

    def start_pending_disable(self, symbol_state: dict, return_mid: float) -> None:
        symbol_state["disable_ticks_waited"] = 0
        symbol_state["disable_return_mid"] = return_mid

    def calculate_intents(self):
        trader_prints = self.prints.setdefault("JUMP", {})

        for symbol, asset in self.assets.items():
            symbol_state = self.get_symbol_state(symbol)
            current_mid = asset.wall_mid
            action = "idle"
            price_move = 0.0
            resumed_from_pending_disable = False

            if current_mid is None:
                if (
                    symbol_state["active"]
                    and not symbol_state["awaiting_first_move"]
                    and symbol_state["disable_return_mid"] is None
                ):
                    asset.position_locked = True
                self.persist_symbol_state(symbol, symbol_state)
                trader_prints[symbol] = {
                    "active": symbol_state["active"],
                    "awaiting_first_move": symbol_state["awaiting_first_move"],
                    "stable_ticks": symbol_state["stable_ticks"],
                    "move_ticks": symbol_state["move_ticks"],
                    "last_move": symbol_state["last_move"],
                    "disable_ticks_waited": symbol_state["disable_ticks_waited"],
                    "disable_return_mid": symbol_state["disable_return_mid"],
                    "mid": None,
                    "action": "no_mid_pending_disable" if symbol_state["disable_return_mid"] is not None else "no_mid",
                }
                continue

            previous_mid = symbol_state["last_wall_mid"]
            if previous_mid is None:
                symbol_state["last_wall_mid"] = current_mid
                self.persist_symbol_state(symbol, symbol_state)
                trader_prints[symbol] = {
                    "active": symbol_state["active"],
                    "awaiting_first_move": symbol_state["awaiting_first_move"],
                    "stable_ticks": symbol_state["stable_ticks"],
                    "move_ticks": symbol_state["move_ticks"],
                    "last_move": symbol_state["last_move"],
                    "mid": current_mid,
                    "action": "seed",
                }
                continue

            if current_mid == previous_mid:
                symbol_state["stable_ticks"] += 1
                symbol_state["move_ticks"] = 0
            else:
                price_move = current_mid - previous_mid
                symbol_state["last_move"] = LONG if current_mid > previous_mid else SHORT
                symbol_state["move_ticks"] += 1
                symbol_state["stable_ticks"] = 0

            if symbol_state["disable_return_mid"] is not None:
                if current_mid == symbol_state["disable_return_mid"]:
                    self.clear_pending_disable(symbol_state)
                    resumed_from_pending_disable = True
                    action = "resume_pending_disable"
                else:
                    symbol_state["disable_ticks_waited"] += 1
                    if symbol_state["disable_ticks_waited"] >= self.DISABLE_GRACE_TICKS:
                        symbol_state["active"] = False
                        symbol_state["awaiting_first_move"] = False
                        symbol_state["move_ticks"] = 0
                        self.clear_pending_disable(symbol_state)
                        asset.orders_to_reach_target(
                            symbol=symbol,
                            order_depth=self.state.order_depths.get(symbol, OrderDepth()),
                            current_position=asset.expected_position,
                            target=0,
                        )
                        action = "disable_timeout_flatten"
                    else:
                        action = "await_disable_return"

                if symbol_state["disable_return_mid"] is not None or action == "disable_timeout_flatten":
                    symbol_state["last_wall_mid"] = current_mid
                    self.persist_symbol_state(symbol, symbol_state)
                    trader_prints[symbol] = {
                        "active": symbol_state["active"],
                        "awaiting_first_move": symbol_state["awaiting_first_move"],
                        "stable_ticks": symbol_state["stable_ticks"],
                        "move_ticks": symbol_state["move_ticks"],
                        "last_move": symbol_state["last_move"],
                        "disable_ticks_waited": symbol_state["disable_ticks_waited"],
                        "disable_return_mid": symbol_state["disable_return_mid"],
                        "mid": current_mid,
                        "price_move": price_move,
                        "action": action,
                        "expected_position": asset.expected_position,
                    }
                    continue

            if not symbol_state["active"] and symbol_state["stable_ticks"] >= self.TICKS_TO_ACTIVATE and symbol_state["last_move"] != 0:
                symbol_state["active"] = True
                symbol_state["awaiting_first_move"] = True
                symbol_state["move_ticks"] = 0
                action = "activate"

            if symbol_state["active"] and symbol_state["awaiting_first_move"] and price_move != 0:
                if abs(price_move) < self.MIN_FIRST_MOVE:
                    symbol_state["active"] = False
                    symbol_state["awaiting_first_move"] = False
                    symbol_state["move_ticks"] = 0
                    action = "cancel_small_first_move"
                else:
                    symbol_state["awaiting_first_move"] = False
                    action = "confirm"

            if (
                symbol_state["active"]
                and not symbol_state["awaiting_first_move"]
                and not resumed_from_pending_disable
                and price_move != 0
                and not (abs(price_move) < self.MAX_SMALL_MOVE or abs(price_move) > self.MIN_LARGE_MOVE)
            ):
                symbol_state["move_ticks"] = 0
                self.start_pending_disable(symbol_state, previous_mid)
                action = "deactivate_filtered_move_pending"

            if symbol_state["active"] and not symbol_state["awaiting_first_move"] and symbol_state["disable_return_mid"] is None:
                target_pos = self.target_from_last_move(symbol_state["last_move"])
                asset.position_locked = True
                if target_pos is not None:
                    asset.orders_to_reach_target(
                        symbol=symbol,
                        order_depth=self.state.order_depths.get(symbol, OrderDepth()),
                        current_position=asset.expected_position,
                        target=target_pos,
                    )
                    if resumed_from_pending_disable:
                        action = "resume_long" if target_pos > 0 else "resume_short"
                    else:
                        action = "long" if target_pos > 0 else "short"
                else:
                    action = "resume_active_wait" if resumed_from_pending_disable else "active_wait"

            symbol_state["last_wall_mid"] = current_mid
            self.persist_symbol_state(symbol, symbol_state)
            trader_prints[symbol] = {
                "active": symbol_state["active"],
                "awaiting_first_move": symbol_state["awaiting_first_move"],
                "stable_ticks": symbol_state["stable_ticks"],
                "move_ticks": symbol_state["move_ticks"],
                "last_move": symbol_state["last_move"],
                "disable_ticks_waited": symbol_state["disable_ticks_waited"],
                "disable_return_mid": symbol_state["disable_return_mid"],
                "mid": current_mid,
                "price_move": price_move,
                "action": action,
                "expected_position": asset.expected_position,
            }


class PebblesTrader:
    STATE_KEY = "pebbles"

    def __init__(self, state: TradingState, prints: dict, assets: dict[str, ProductTrader], new_trader_data: dict):
        self.state = state
        self.prints = prints
        self.assets = assets
        self.new_trader_data = new_trader_data
        self.last_trader_data = self.get_last_trader_data()

    def get_last_trader_data(self) -> dict:
        try:
            trader_data = json.loads(self.state.traderData) if self.state.traderData else {}
        except Exception:
            return {}
        stored = trader_data.get(self.STATE_KEY, {})
        if isinstance(stored, dict):
            return stored
        return {}

    def get_symbol_state(self, symbol: str) -> dict:
        previous = self.last_trader_data.get(symbol, {})
        return {
            "long_ticks_remaining": max(0, int(previous.get("long_ticks_remaining", 0))),
            "short_ticks_remaining": max(0, int(previous.get("short_ticks_remaining", 0))),
            "long_strength": float(previous.get("long_strength", 0.0)),
            "short_strength": float(previous.get("short_strength", 0.0)),
            "long_score_weight": float(previous.get("long_score_weight", 1.0)),
            "short_score_weight": float(previous.get("short_score_weight", 1.0)),
        }

    def persist_symbol_state(self, symbol: str, symbol_state: dict) -> None:
        strategy_state = self.new_trader_data.setdefault(self.STATE_KEY, {})
        strategy_state[symbol] = symbol_state

    def target_from_move(self, move: float, direction_multiplier: int, target_position: int) -> int:
        move_direction = LONG if move > 0 else SHORT
        return move_direction * direction_multiplier * target_position

    def get_previous_own_trade_combo(self) -> dict[str, str]:
        combo = {symbol: "." for symbol in PEBBLES_PRODUCTS}
        own_trades = self.state.own_trades if isinstance(self.state.own_trades, dict) else {}
        for symbol in PEBBLES_PRODUCTS:
            net_qty = 0
            for trade in own_trades.get(symbol, []):
                if getattr(trade, "buyer", "") == "SUBMISSION":
                    net_qty += int(getattr(trade, "quantity", 0))
                if getattr(trade, "seller", "") == "SUBMISSION":
                    net_qty -= int(getattr(trade, "quantity", 0))
            if net_qty > 0:
                combo[symbol] = "B"
            elif net_qty < 0:
                combo[symbol] = "S"
        return combo

    def update_signal_state(self, target: str, settings: dict) -> tuple[dict, dict]:
        symbol_state = self.get_symbol_state(target)
        signal_rules = settings.get("signals", {})
        signal_prints: dict[str, dict] = {}
        previous_trade_combo = self.get_previous_own_trade_combo()

        for signal_name in ("long", "short"):
            ticks_key = f"{signal_name}_ticks_remaining"
            strength_key = f"{signal_name}_strength"
            weight_key = f"{signal_name}_score_weight"
            rules = get_signal_rule_list(signal_rules, signal_name)
            signal_print = {
                "active": symbol_state[ticks_key] > 0,
            }

            if not rules:
                signal_prints[signal_name] = signal_print
                continue
            triggered = False
            best_trigger_score = float("-inf")
            active_rule = None
            rule_prints = []

            for rule in rules:
                rule_kind = str(rule.get("kind", "price_move")).lower()
                hold_ticks = max(0, int(rule.get("hold_ticks", 0)))
                score_weight = float(rule.get("score_weight", 1.0))

                if rule_kind == "own_trade_combo":
                    expected_combo = rule.get("combo", {})
                    combo_match = isinstance(expected_combo, dict) and all(
                        previous_trade_combo.get(symbol, ".") == expected_side
                        for symbol, expected_side in expected_combo.items()
                    )
                    rule_print = {
                        "kind": rule_kind,
                        "combo": expected_combo,
                        "observed_combo": previous_trade_combo,
                        "matched": combo_match,
                        "triggered": combo_match,
                        "hold_ticks": hold_ticks,
                        "score_weight": score_weight,
                    }
                    if combo_match and score_weight > best_trigger_score:
                        best_trigger_score = score_weight
                        symbol_state[ticks_key] = hold_ticks
                        symbol_state[strength_key] = 0.0
                        symbol_state[weight_key] = score_weight
                        active_rule = rule_print
                        triggered = True
                    rule_prints.append(rule_print)
                    continue

                source_symbol = rule.get("source")
                source_asset = self.assets.get(source_symbol) if isinstance(source_symbol, str) else None
                lag = max(1, int(rule.get("lag", 1)))
                direction = str(rule.get("direction", "up")).lower()
                threshold = float(rule.get("threshold", 0.0))
                current_mid = source_asset.wall_mid if source_asset is not None else None
                lagged_mid = source_asset.get_price_from_history(lag) if source_asset is not None else None
                move = None
                threshold_move = threshold
                strength = 0.0
                rule_triggered = False

                if current_mid is not None and lagged_mid is not None:
                    move = current_mid - lagged_mid
                    if direction == "down":
                        threshold_move = -threshold
                    rule_triggered = move >= threshold if direction != "down" else move <= -threshold
                    if rule_triggered:
                        trigger_gap = abs(move) - threshold
                        strength = max(0.0, trigger_gap / max(threshold, 1.0))
                        candidate_score = score_weight * (1.0 + strength)
                        if candidate_score > best_trigger_score:
                            best_trigger_score = candidate_score
                            symbol_state[ticks_key] = hold_ticks
                            symbol_state[strength_key] = strength
                            symbol_state[weight_key] = score_weight
                            active_rule = {
                                "kind": rule_kind,
                                "source": source_symbol,
                                "direction": direction,
                                "lag": lag,
                                "threshold": threshold,
                                "move": round(move, 4),
                                "triggered": True,
                                "hold_ticks": hold_ticks,
                                "score_weight": score_weight,
                            }
                            triggered = True

                rule_prints.append(
                    {
                        "kind": rule_kind,
                        "source": source_symbol,
                        "direction": direction,
                        "lag": lag,
                        "threshold": threshold,
                        "threshold_move": round(threshold_move, 4) if move is not None else None,
                        "move": round(move, 4) if move is not None else None,
                        "triggered": rule_triggered,
                        "hold_ticks": hold_ticks,
                        "score_weight": score_weight,
                        "strength": round(strength, 4),
                    }
                )

            if symbol_state[ticks_key] > 0:
                if not triggered:
                    symbol_state[ticks_key] -= 1
                signal_print["active"] = True
            else:
                symbol_state[strength_key] = 0.0
                symbol_state[weight_key] = 1.0
                signal_print["active"] = False

            signal_print.update(
                {
                    "triggered": triggered,
                    "ticks_remaining": symbol_state[ticks_key],
                    "strength": round(symbol_state[strength_key], 4),
                    "score_weight": round(symbol_state[weight_key], 4),
                    "active_rule": active_rule,
                    "rules": rule_prints,
                }
            )
            signal_prints[signal_name] = signal_print

        self.persist_symbol_state(target, symbol_state)
        return symbol_state, signal_prints

    def regime_direction(self, symbol_state: dict, settings: dict) -> int:
        long_score = 0.0
        short_score = 0.0
        if symbol_state["long_ticks_remaining"] > 0:
            long_weight = float(symbol_state.get("long_score_weight", 1.0))
            long_score = long_weight * (1.0 + symbol_state["long_strength"])
        if symbol_state["short_ticks_remaining"] > 0:
            short_weight = float(symbol_state.get("short_score_weight", 1.0))
            short_score = short_weight * (1.0 + symbol_state["short_strength"])
        if long_score > short_score:
            return LONG
        if short_score > long_score:
            return SHORT
        return NEUTRAL

    def synthetic_input_price(self, symbol: str) -> Optional[float]:
        asset = self.assets.get(symbol)
        if asset is None:
            return None
        if asset.wall_mid is not None:
            return asset.wall_mid
        return asset.get_reference_price()

    def synthetic_fair(self, target: str) -> Optional[float]:
        component_sum = 0.0
        for symbol in PEBBLES_PRODUCTS:
            if symbol == target:
                continue
            component_price = self.synthetic_input_price(symbol)
            if component_price is None:
                return None
            component_sum += component_price
        return PEBBLES_ANCHOR - component_sum

    def calculate_symbol_orders(self, target: str, settings: dict) -> None:
        asset = self.assets.get(target)
        trader_prints = self.prints.setdefault("PEBBLES", {})
        symbol_prints = trader_prints.setdefault(target, {})
        if asset is None:
            symbol_prints["status"] = "missing_asset"
            return

        fair = self.synthetic_fair(target)
        if fair is None:
            symbol_prints["status"] = "missing_component_price"
            return

        symbol_state, signal_prints = self.update_signal_state(target, settings)
        regime_direction = self.regime_direction(symbol_state, settings)

        current_position = asset.expected_position
        reservation_shift = float(settings["own_position_skew"]) * current_position
        max_reservation_shift = float(settings["max_reservation_shift"])
        reservation_shift = max(-max_reservation_shift, min(max_reservation_shift, reservation_shift))
        reservation_price = fair - reservation_shift
        reservation_price -= float(settings.get("default_bearish_bias", 0.0))

        signal_reservation_shift = float(settings.get("signal_reservation_shift", 0.0))
        reservation_price += regime_direction * signal_reservation_shift

        target_half_spread = float(settings["target_half_spread"])
        target_bid = math.floor(reservation_price - target_half_spread)
        target_ask = math.ceil(reservation_price + target_half_spread)

        if asset.best_bid is not None:
            quote_bid = min(target_bid, asset.best_bid + 1)
        else:
            quote_bid = math.floor(reservation_price - float(settings["fallback_half_spread"]))

        if asset.best_ask is not None:
            quote_ask = max(target_ask, asset.best_ask - 1)
        else:
            quote_ask = math.ceil(reservation_price + float(settings["fallback_half_spread"]))

        if asset.best_ask is not None:
            quote_bid = min(quote_bid, asset.best_ask - 1)
        if asset.best_bid is not None:
            quote_ask = max(quote_ask, asset.best_bid + 1)

        if quote_bid >= quote_ask:
            quote_bid = math.floor(reservation_price - 1)
            quote_ask = math.ceil(reservation_price + 1)

        quote_bid = max(1, quote_bid)
        quote_ask = max(quote_bid + 1, quote_ask)

        signal_target_position = int(settings.get("signal_target_position", 0))
        one_sided_position_limit = int(settings["one_sided_position_limit"])

        if regime_direction == LONG:
            band_low = signal_target_position
            band_high = one_sided_position_limit
        elif regime_direction == SHORT:
            band_low = -one_sided_position_limit
            band_high = -signal_target_position
        else:
            band_low = -one_sided_position_limit
            band_high = one_sided_position_limit

        band_low = max(-POS_LIMIT, min(POS_LIMIT, band_low))
        band_high = max(-POS_LIMIT, min(POS_LIMIT, band_high))

        taker_edge = float(settings.get("taker_edge", 0.0))
        take_buy_upto = math.floor(reservation_price - taker_edge)
        take_sell_down_to = math.ceil(reservation_price + taker_edge)
        if regime_direction == LONG:
            taker_buy_target = band_high
            taker_sell_target = band_low
        elif regime_direction == SHORT:
            taker_buy_target = band_high
            taker_sell_target = band_low
        else:
            taker_buy_target = min(band_high, signal_target_position)
            taker_sell_target = max(band_low, -signal_target_position)

        asset.position_locked = True
        took_liquidity = False
        if asset.best_ask is not None and asset.best_ask <= take_buy_upto and current_position < taker_buy_target:
            asset.orders_to_reach_target(
                symbol=target,
                order_depth=self.state.order_depths.get(target, OrderDepth()),
                current_position=asset.expected_position,
                target=taker_buy_target,
                max_buy_price=take_buy_upto,
                post_remainder=False,
            )
            took_liquidity = True

        if asset.best_bid is not None and asset.best_bid >= take_sell_down_to and asset.expected_position > taker_sell_target:
            asset.orders_to_reach_target(
                symbol=target,
                order_depth=self.state.order_depths.get(target, OrderDepth()),
                current_position=asset.expected_position,
                target=taker_sell_target,
                min_sell_price=take_sell_down_to,
                post_remainder=False,
            )
            took_liquidity = True

        current_position = asset.expected_position

        bid_size = max(0, band_high - current_position)
        ask_size = max(0, current_position - band_low)

        bid_size = min(bid_size, asset.max_allowed_buy_volume)
        ask_size = min(ask_size, asset.max_allowed_sell_volume)

        if bid_size > 0 and quote_bid is not None:
            asset.bid(quote_bid, bid_size, logging=False)
        if ask_size > 0 and quote_ask is not None:
            asset.ask(quote_ask, ask_size, logging=False)

        symbol_prints.update(
            {
                "status": "active",
                "fair": round(fair, 4),
                "reservation_price": round(reservation_price, 4),
                "reservation_shift": round(reservation_shift, 4),
                "position": current_position,
                "taker_edge": taker_edge,
                "take_buy_upto": take_buy_upto,
                "take_sell_down_to": take_sell_down_to,
                "taker_buy_target": taker_buy_target,
                "taker_sell_target": taker_sell_target,
                "took_liquidity": took_liquidity,
                "best_bid": asset.best_bid,
                "best_ask": asset.best_ask,
                "quote_bid": quote_bid if bid_size > 0 else None,
                "quote_ask": quote_ask if ask_size > 0 else None,
                "bid_size": bid_size,
                "ask_size": ask_size,
                "band_low": band_low,
                "band_high": band_high,
                "wall_mid": asset.wall_mid,
                "regime_direction": regime_direction,
                "signals": signal_prints,
            }
        )

    def _calculate_two_sided_mm(self, target: str, settings: dict, asset: "ProductTrader") -> None:
        """True two-sided market maker: post both bid and ask, use actual market mid as fair."""
        trader_prints = self.prints.setdefault("PEBBLES", {})
        symbol_prints = trader_prints.setdefault(target, {})

        current_position = asset.expected_position
        inventory_skew_per_lot = float(settings.get("inventory_skew_per_lot", 1.5))
        one_sided_limit = int(settings.get("one_sided_limit", POS_LIMIT - 2))
        drift_correction = float(settings.get("drift_correction", 0.0))
        closeout_start = int(settings.get("closeout_start_timestamp", 950_000))

        if self.state.timestamp >= closeout_start:
            asset.position_locked = True
            if current_position != 0:
                asset.orders_to_reach_target(
                    symbol=target,
                    order_depth=self.state.order_depths.get(target, OrderDepth()),
                    current_position=current_position,
                    target=0,
                    max_buy_price=asset.best_ask,
                    min_sell_price=asset.best_bid,
                    post_remainder=False,
                )
            symbol_prints["status"] = "closeout"
            return

        if asset.best_bid is None or asset.best_ask is None:
            symbol_prints["status"] = "no_market"
            return

        market_mid = (asset.best_bid + asset.best_ask) / 2.0 + drift_correction
        # Shift effective fair value down when long, up when short, to mean-revert inventory.
        effective_mid = market_mid - current_position * inventory_skew_per_lot

        # Quote inside the spread, but never above/below our effective fair value.
        # bid: at most best_bid+1 (inside), at most floor(effective_mid - 0.5) (below fair)
        # ask: at least best_ask-1 (inside), at least ceil(effective_mid + 0.5) (above fair)
        quote_bid = min(asset.best_bid + 1, math.floor(effective_mid - 0.5))
        quote_ask = max(asset.best_ask - 1, math.ceil(effective_mid + 0.5))

        # Guard: ensure bid < ask
        if quote_bid >= quote_ask:
            mid_int = int(math.floor(effective_mid))
            quote_bid = mid_int - 1
            quote_ask = mid_int + 1

        bid_size = max(0, one_sided_limit - current_position)
        ask_size = max(0, current_position + one_sided_limit)

        bid_size = min(bid_size, asset.max_allowed_buy_volume)
        ask_size = min(ask_size, asset.max_allowed_sell_volume)

        # One-sided: stop adding to the losing side near position limits
        if current_position >= one_sided_limit:
            bid_size = 0
        if current_position <= -one_sided_limit:
            ask_size = 0

        asset.position_locked = False

        if bid_size > 0:
            asset.bid(int(quote_bid), bid_size, logging=False)
        if ask_size > 0:
            asset.ask(int(quote_ask), ask_size, logging=False)

        symbol_prints.update({
            "status": "two_sided_mm",
            "market_mid": round(market_mid, 2),
            "effective_mid": round(effective_mid, 2),
            "quote_bid": quote_bid,
            "quote_ask": quote_ask,
            "bid_size": bid_size,
            "ask_size": ask_size,
            "position": current_position,
        })

    def calculate_orders(self) -> None:
        for target, settings in PEBBLES_CONFIG.items():
            if not bool(settings.get("enabled", False)):
                continue
            self.calculate_symbol_orders(target, settings)



def _wall_price(levels: dict[int, int], side: str) -> Optional[int]:
    if not levels:
        return None
    sorted_prices = sorted(levels.keys(), reverse=(side == "bid"))
    for price in sorted_prices:
        if abs(levels[price]) >= MM_V12_WALL_VOL_THRESH:
            return price
    return sorted_prices[0]


class _WallMidMMTrader:
    PRODUCTS: List[str] = []
    LOG_KEY = "MM"

    def __init__(self, state: TradingState, prints: dict, assets: dict[str, ProductTrader]):
        self.state = state
        self.prints = prints
        self.assets = assets

    def calculate_orders(self) -> None:
        log_bucket = self.prints.setdefault(self.LOG_KEY, {})
        for product in self.PRODUCTS:
            asset = self.assets.get(product)
            if asset is None or asset.position_locked:
                continue
            if asset.best_bid is None or asset.best_ask is None:
                continue
            if asset.best_ask <= asset.best_bid:
                continue
            self._mm_one_product(asset, log_bucket)
            asset.position_locked = True

    def _mm_one_product(self, asset: ProductTrader, log_bucket: dict) -> None:
        best_bid, best_ask = asset.best_bid, asset.best_ask
        half_spread = (best_ask - best_bid) / 2.0

        bid_wall = _wall_price(asset.mkt_buy_orders, "bid") or best_bid
        ask_wall = _wall_price(asset.mkt_sell_orders, "ask") or best_ask
        wall_mid = (bid_wall + ask_wall) / 2.0

        position_in = asset.expected_position
        reservation = wall_mid - MM_V12_SKEW_PER_UNIT * position_in

        for ask_price, ask_vol in sorted(asset.mkt_sell_orders.items()):
            if ask_price <= reservation - half_spread and asset.max_allowed_buy_volume > 0:
                asset.bid(ask_price, min(asset.max_allowed_buy_volume, ask_vol), logging=False)
            else:
                break

        for bid_price, bid_vol in sorted(asset.mkt_buy_orders.items(), reverse=True):
            if bid_price >= reservation + half_spread and asset.max_allowed_sell_volume > 0:
                asset.ask(bid_price, min(asset.max_allowed_sell_volume, bid_vol), logging=False)
            else:
                break

        our_bid = best_bid + 1
        our_ask = best_ask - 1
        if our_ask <= our_bid:
            our_bid, our_ask = best_bid, best_ask

        if position_in < MM_V12_HARD_PULL and asset.max_allowed_buy_volume > 0:
            asset.bid(our_bid, min(MM_V12_QUOTE_SIZE, asset.max_allowed_buy_volume), logging=False)
        if position_in > -MM_V12_HARD_PULL and asset.max_allowed_sell_volume > 0:
            asset.ask(our_ask, min(MM_V12_QUOTE_SIZE, asset.max_allowed_sell_volume), logging=False)

        log_bucket[asset.name] = {
            "wall_mid": round(wall_mid, 4),
            "bid_wall": bid_wall,
            "ask_wall": ask_wall,
            "pos_in": position_in,
            "pos_out": asset.expected_position,
        }


class TranslatorMMTrader(_WallMidMMTrader):
    LOG_KEY = "TRANSLATOR_MM"
    PRODUCTS = [
        "TRANSLATOR_ASTRO_BLACK",
        "TRANSLATOR_ECLIPSE_CHARCOAL",
        "TRANSLATOR_GRAPHITE_MIST",
        "TRANSLATOR_SPACE_GRAY",
        "TRANSLATOR_VOID_BLUE",
    ]


class GalaxySoundsMMTrader(_WallMidMMTrader):
    LOG_KEY = "GALAXY_SOUNDS_MM"
    PRODUCTS = [
        "GALAXY_SOUNDS_BLACK_HOLES",
        "GALAXY_SOUNDS_DARK_MATTER",
        "GALAXY_SOUNDS_PLANETARY_RINGS",
        "GALAXY_SOUNDS_SOLAR_FLAMES", # Not a good product!
        "GALAXY_SOUNDS_SOLAR_WINDS",
    ]


class UVTurnPointOverlay:
    """Small delayed-turn overlay for UV visors.

    Proven links:
    - YELLOW turn -> delayed ORANGE target
    - RED turn -> delayed MAGENTA target

    This stays deliberately non-invasive: it skips products already locked or
    carrying another strategy intent, uses small passive targets, and locks the
    default max-MM fallback only while its own signal is active.
    """

    STATE_KEY = "uv_turnpoint"
    LINKS = (
        ("UV_VISOR_YELLOW", "UV_VISOR_ORANGE"),
        ("UV_VISOR_RED", "UV_VISOR_MAGENTA"),
    )
    LAG_TS = 400_000
    HOLD_TS = 80_000
    TARGET_POS = 3
    MIN_TURN_GAP_TS = 80_000
    MIN_DIFF_ABS = 25.0
    FAST_ALPHA = 0.025
    SLOW_ALPHA = 0.004
    INTENT_WEIGHT = 0.8

    def __init__(
        self,
        state: TradingState,
        prints: dict,
        assets: dict[str, ProductTrader],
        new_trader_data: dict,
        last_trader_data: dict,
    ):
        self.state = state
        self.prints = prints
        self.assets = assets
        self.new_trader_data = new_trader_data
        raw_state = last_trader_data.get(self.STATE_KEY, {}) if isinstance(last_trader_data, dict) else {}
        self.overlay_state = raw_state if isinstance(raw_state, dict) else {}

    def calculate_intents(self) -> None:
        logs = self.prints.setdefault("UV_TURNPOINT", {})
        for leader_name, lagger_name in self.LINKS:
            leader = self.assets.get(leader_name)
            lagger = self.assets.get(lagger_name)
            if leader is None or lagger is None:
                continue

            leader_mid = leader.get_reference_price()
            if leader_mid is None:
                continue

            link_key = leader_name + ">" + lagger_name
            link_state = self.get_link_state(link_key)
            self.update_link_state(link_state, float(leader_mid))
            self.overlay_state[link_key] = link_state

            direction = self.active_direction(link_state)
            if direction == 0:
                continue
            if lagger.position_locked or lagger.intents:
                continue

            target = max(-POS_LIMIT, min(POS_LIMIT, direction * self.TARGET_POS))
            if direction > 0:
                max_buy_price = lagger.best_bid + 1 if lagger.best_bid is not None else None
                min_sell_price = None
            else:
                max_buy_price = None
                min_sell_price = lagger.best_ask - 1 if lagger.best_ask is not None else None

            lagger.add_intent(
                strategy_name="uv_turnpoint:" + link_key,
                target_pos=target,
                weight=self.INTENT_WEIGHT,
                max_buy_price=max_buy_price,
                min_sell_price=min_sell_price,
            )
            lagger.lock_buy_mm = True
            lagger.lock_sell_mm = True
            logs[lagger_name] = {
                "leader": leader_name,
                "direction": direction,
                "target": target,
                "diff": round(float(link_state.get("last_diff", 0.0)), 2),
            }

        self.persist()

    def update_link_state(self, link_state: dict, leader_mid: float) -> None:
        ts = int(self.state.timestamp)
        fast = link_state.get("fast")
        slow = link_state.get("slow")
        if not isinstance(fast, (int, float)) or not isinstance(slow, (int, float)):
            link_state["fast"] = leader_mid
            link_state["slow"] = leader_mid
            link_state["last_diff"] = 0.0
            link_state["last_regime"] = 0
            link_state["last_turn_ts"] = -10**9
            link_state["events"] = []
            return

        fast = (1.0 - self.FAST_ALPHA) * float(fast) + self.FAST_ALPHA * leader_mid
        slow = (1.0 - self.SLOW_ALPHA) * float(slow) + self.SLOW_ALPHA * leader_mid
        diff = fast - slow
        last_regime = int(link_state.get("last_regime", 0))
        last_turn_ts = int(link_state.get("last_turn_ts", -10**9))
        events = self.valid_events(link_state)

        current_regime = last_regime
        if diff > self.MIN_DIFF_ABS:
            current_regime = 1
        elif diff < -self.MIN_DIFF_ABS:
            current_regime = -1

        direction = 0
        if last_regime != 0 and current_regime != last_regime:
            direction = current_regime

        if direction != 0 and ts - last_turn_ts >= self.MIN_TURN_GAP_TS:
            events.append(
                {
                    "due": ts + self.LAG_TS,
                    "until": ts + self.LAG_TS + self.HOLD_TS,
                    "direction": direction,
                }
            )
            link_state["last_turn_ts"] = ts

        link_state["fast"] = fast
        link_state["slow"] = slow
        link_state["last_diff"] = diff
        link_state["last_regime"] = current_regime
        link_state["events"] = [event for event in events if int(event.get("until", -1)) >= ts]

    def active_direction(self, link_state: dict) -> int:
        ts = int(self.state.timestamp)
        score = 0
        for event in self.valid_events(link_state):
            due = int(event.get("due", 0))
            until = int(event.get("until", -1))
            if due <= ts <= until:
                score += int(event.get("direction", 0))
        if score > 0:
            return 1
        if score < 0:
            return -1
        return 0

    def get_link_state(self, link_key: str) -> dict:
        raw_state = self.overlay_state.get(link_key, {})
        return raw_state if isinstance(raw_state, dict) else {}

    def valid_events(self, link_state: dict) -> list[dict]:
        events = link_state.get("events", [])
        if not isinstance(events, list):
            return []
        return [event for event in events if isinstance(event, dict)]

    def persist(self) -> None:
        compact = {}
        for leader_name, lagger_name in self.LINKS:
            link_key = leader_name + ">" + lagger_name
            link_state = self.get_link_state(link_key)
            compact[link_key] = {
                "fast": link_state.get("fast"),
                "slow": link_state.get("slow"),
                "last_diff": link_state.get("last_diff"),
                "last_regime": link_state.get("last_regime", 0),
                "last_turn_ts": link_state.get("last_turn_ts", -10**9),
                "events": self.valid_events(link_state)[-4:],
            }
        self.new_trader_data[self.STATE_KEY] = compact


class Trader:
    def run(self, state: TradingState):
        prints: dict = {
            "GENERAL": {
                "TIMESTAMP": state.timestamp,
                "POSITIONS": state.position,
            }
        }

        new_data: dict = {}
        result: dict[str, list[Order]] = {}

        try:
            last_trader_data = json.loads(state.traderData) if state.traderData else {}
        except Exception:
            last_trader_data = {}

        assets = {
            product: ProductTrader(product, state, prints, new_data, last_trader_data=last_trader_data)
            for product in state.listings.keys()
        }
        etf_traders = [EtfTrader(state, prints, assets, settings, new_data, last_trader_data) for settings in CORRELATIONS]
        da_fuck_traders = [JumpTrader(state, prints, assets, new_data)]
        pebbles_trader = PebblesTrader(state, prints, assets, new_data)
        mm_traders = [
            TranslatorMMTrader(state, prints, assets),
            GalaxySoundsMMTrader(state, prints, assets),
        ]
        uv_overlay = UVTurnPointOverlay(state, prints, assets, new_data, last_trader_data)

        for da_fuck_trader in da_fuck_traders:
            da_fuck_trader.calculate_intents()


        for mm_trader in mm_traders:
            mm_trader.calculate_orders()


        pebbles_trader.calculate_orders()

        for etf_trader in etf_traders:
            etf_trader.calculate_intents()

        uv_overlay.calculate_intents()

        for asset_name, asset_trader in assets.items():
            orders = asset_trader.get_orders()
            result[asset_name] = orders
        
        try:
            final_trader_data = json.dumps(new_data)
        except Exception:
            final_trader_data = ""

        # try:
        #     print(json.dumps(prints))
        # except Exception:
        #     pass

        return result, 0, final_trader_data
