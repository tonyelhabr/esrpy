from datetime import UTC, datetime

import numpy as np
import pytest

from esrpy.config import BatteryConfig, BatteryOptimizationConfig
from esrpy.schemas import BatteryState
from esrpy.strategies import ConfigurableOptimizationStrategy


class TestConfigurableOptimizationStrategy:
    """Test suite for ConfigurableOptimizationStrategy."""

    @pytest.fixture
    def battery_config(self):
        """Standard battery configuration for testing."""
        return BatteryConfig(
            capacity_mwh=200.0,
            max_power_mw=200.0,
            soc_min_pct=0.10,
            soc_max_pct=0.90,
            roundtrip_efficiency=0.90,
        )

    @pytest.fixture
    def opt_config(self):
        """Optimization config with no price thresholds."""
        return BatteryOptimizationConfig(
            horizon_intervals=11,
            min_buy_price=None,
            max_sell_price=None,
        )

    def test_charge_when_prices_rising(self, battery_config, opt_config):
        """Should charge when prices are low and expected to rise."""
        strategy = ConfigurableOptimizationStrategy(opt_config)

        initial_state = BatteryState(
            timestamp=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
            soc_mwh=25.0,
        )

        forecasted_prices = np.array([20, 22, 25, 30, 40, 55, 60, 75, 75, 75, 75])

        offer = strategy.make_offer(
            state=initial_state,
            config=battery_config,
            forecasted_prices=forecasted_prices,
        )

        assert offer.power_mw < 0
        assert offer.timestamp == initial_state.timestamp

    def test_discharge_when_prices_falling(self, battery_config, opt_config):
        """Should discharge when prices are high and expected to fall."""
        strategy = ConfigurableOptimizationStrategy(opt_config)

        initial_state = BatteryState(
            timestamp=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC), soc_mwh=175.0
        )

        forecasted_prices = np.array([60, 55, 40, 30, 25, 22, 20, 20, 20, 20, 20])

        offer = strategy.make_offer(
            state=initial_state,
            config=battery_config,
            forecasted_prices=forecasted_prices,
        )

        assert offer.power_mw > 0

    def test_discharge_with_flat_positive_prices(self, battery_config, opt_config):
        """With flat positive prices and available energy, should discharge."""
        strategy = ConfigurableOptimizationStrategy(opt_config)

        initial_state = BatteryState(
            timestamp=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
            soc_mwh=50.0,
        )

        forecasted_prices = np.array([30.0] * 11)

        offer = strategy.make_offer(
            state=initial_state,
            config=battery_config,
            forecasted_prices=forecasted_prices,
        )

        assert offer.power_mw > 0

    def test_respects_soc_constraints(self, battery_config, opt_config):
        """Should not violate SoC limits."""
        strategy = ConfigurableOptimizationStrategy(opt_config)

        initial_state = BatteryState(
            timestamp=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
            soc_mwh=20.0,
        )

        forecasted_prices = np.array([2000.0] * 11)

        offer = strategy.make_offer(
            state=initial_state,
            config=battery_config,
            forecasted_prices=forecasted_prices,
        )

        # Cannot discharge when already at minimum SoC
        assert offer.power_mw <= 0

    def test_respects_power_limits(self, battery_config, opt_config):
        """Should not exceed power rating."""
        strategy = ConfigurableOptimizationStrategy(opt_config)

        initial_state = BatteryState(
            timestamp=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
            soc_mwh=200.0,
        )

        forecasted_prices = np.array([2000.0] * 11)

        offer = strategy.make_offer(
            state=initial_state,
            config=battery_config,
            forecasted_prices=forecasted_prices,
        )

        assert abs(offer.power_mw) <= battery_config.max_power_mw

    def test_respects_min_buy_price_threshold(self, battery_config):
        """Should not charge if price is above min_buy_price threshold."""
        opt_config = BatteryOptimizationConfig(
            horizon_intervals=11,
            min_buy_price=20.0,
            max_sell_price=None,
        )
        strategy = ConfigurableOptimizationStrategy(opt_config)

        initial_state = BatteryState(
            timestamp=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
            soc_mwh=25.0,
        )

        forecasted_prices = np.array([30, 35, 40, 45, 50, 55, 60, 75, 75, 75, 75])

        offer = strategy.make_offer(
            state=initial_state,
            config=battery_config,
            forecasted_prices=forecasted_prices,
        )

        # Should not charge since first price is above min_buy_price
        assert offer.power_mw >= 0

    def test_respects_max_sell_price_threshold(self, battery_config):
        """Should not discharge if price is below max_sell_price threshold."""
        opt_config = BatteryOptimizationConfig(
            horizon_intervals=11,
            min_buy_price=None,
            max_sell_price=70.0,
        )
        strategy = ConfigurableOptimizationStrategy(opt_config)

        initial_state = BatteryState(
            timestamp=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
            soc_mwh=175.0,
        )

        forecasted_prices = np.array([60, 55, 40, 30, 25, 22, 20, 20, 20, 20, 20])

        offer = strategy.make_offer(
            state=initial_state,
            config=battery_config,
            forecasted_prices=forecasted_prices,
        )

        # Should not discharge since first price is below max_sell_price
        assert offer.power_mw <= 0
