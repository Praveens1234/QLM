import pandas as pd
import numpy as np
import itertools
import logging
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Tuple

# DEAP Imports
from deap import base, creator, tools, algorithms

# Local imports
from backend.core.engine import BacktestEngine
from backend.core.exceptions import OptimizationError
from backend.core.store import MetadataStore

logger = logging.getLogger("QLM.Analytics")

def calculate_market_structure(df: pd.DataFrame) -> dict:
    """
    Calculate basic market structure metrics:
    - Trend (SMA 50 vs 200)
    - Volatility (ATR 14)
    - Support/Resistance (Pivot Points)
    - RSI 14
    """
    if len(df) < 200:
        return {"error": "Not enough data (minimum 200 rows)"}

    # Trend
    sma50 = df['close'].rolling(50).mean().iloc[-1]
    sma200 = df['close'].rolling(200).mean().iloc[-1]
    trend = "Bullish" if sma50 > sma200 else "Bearish"

    # Volatility (ATR)
    high = df['high']
    low = df['low']
    close = df['close']
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(14).mean().iloc[-1]
    volatility_pct = (atr / close.iloc[-1]) * 100

    # RSI
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs)).iloc[-1]

    # Support/Resistance (Simple Pivot High/Low)
    # Just take min/max of last 50 periods
    support = low.tail(50).min()
    resistance = high.tail(50).max()

    return {
        "trend": trend,
        "sma50": round(sma50, 2),
        "sma200": round(sma200, 2),
        "volatility_atr": round(atr, 4),
        "volatility_pct": round(volatility_pct, 2),
        "rsi": round(rsi, 2),
        "support_50": round(support, 2),
        "resistance_50": round(resistance, 2),
        "current_price": round(close.iloc[-1], 2)
    }

def _load_optimization_context(strategy_name: str, dataset_id: str):
    """
    Helper to load data and strategy class once for optimization runs.
    """
    engine = BacktestEngine()
    store = MetadataStore()
    metadata = store.get_dataset(dataset_id)
    if not metadata:
            raise ValueError(f"Dataset {dataset_id} not found")

    df = engine.data_manager.load_dataset(metadata['file_path'])

    versions = engine.strategy_loader._get_versions(strategy_name)
    version = max(versions) if versions else 1
    StrategyClass = engine.strategy_loader.load_strategy_class(strategy_name, version)
    if not StrategyClass:
            raise ValueError(f"Strategy {strategy_name} not found")

    return engine, df, StrategyClass

def optimize_strategy(strategy_name: str, dataset_id: str, param_grid: Dict[str, List[Any]], target_metric: str = "net_profit") -> Dict[str, Any]:
    """
    Perform Grid Search Optimization for a strategy on a dataset.
    Uses ThreadPoolExecutor to run parallel backtests (Numba releases GIL).
    """
    try:
        logger.info(f"Starting Grid Search for {strategy_name} on {dataset_id}...")

        # 1. Generate Parameter Combinations
        keys = list(param_grid.keys())
        values = list(param_grid.values())
        combinations = list(itertools.product(*values))

        total_combos = len(combinations)
        if total_combos == 0:
            raise OptimizationError("Parameter grid is empty.")
        if total_combos > 5000:
            logger.warning(f"Large parameter space: {total_combos} combinations. Consider Genetic Algorithm.")

        # 2. Load Context
        engine, df, StrategyClass = _load_optimization_context(strategy_name, dataset_id)
        
        # Pre-calculate data arrays to avoid repeated copying in threads (Fix for Freeze/Memory Leak)
        precalc_arrays = engine._prepare_data_arrays(df)

        results = []

        def _run_single(params_tuple):
            try:
                params = dict(zip(keys, params_tuple))

                try:
                    strategy_instance = StrategyClass(parameters=params)
                except TypeError:
                     strategy_instance = StrategyClass()
                     if hasattr(strategy_instance, 'set_parameters'):
                         strategy_instance.set_parameters(params)

                res = engine._execute_fast(df, strategy_instance, precalc_arrays=precalc_arrays)
                metrics = res['metrics']

                return {
                    "params": params,
                    "metrics": metrics,
                    "status": "success"
                }
            except Exception as e:
                return {"params": params, "error": str(e), "status": "failed"}

        # Limit workers to 4 on Windows to prevent threading issues/freezes
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(_run_single, combo) for combo in combinations]

            for future in as_completed(futures):
                res = future.result()
                if res['status'] == "success":
                    results.append(res)

        if not results:
            raise OptimizationError("All optimization runs failed.")

        results.sort(key=lambda x: x['metrics'].get(target_metric, -float('inf')), reverse=True)
        best_result = results[0]

        return {
            "strategy": strategy_name,
            "dataset_id": dataset_id,
            "method": "Grid Search",
            "best_params": best_result['params'],
            "best_metrics": best_result['metrics'],
            "top_10": results[:10],
            "total_runs": len(results)
        }

    except Exception as e:
        logger.error(f"Grid Search failed: {e}")
        raise OptimizationError(f"Grid Search failed: {str(e)}")

def optimize_strategy_genetic(strategy_name: str, dataset_id: str, param_grid: Dict[str, List[Any]], population_size: int = 50, generations: int = 10, target_metric: str = "net_profit") -> Dict[str, Any]:
    """
    Perform Genetic Algorithm Optimization using DEAP.
    """
    try:
        logger.info(f"Starting Genetic Optimization for {strategy_name}...")

        # 1. Setup Context
        engine, df, StrategyClass = _load_optimization_context(strategy_name, dataset_id)
        
        # Pre-calculate arrays
        precalc_arrays = engine._prepare_data_arrays(df)

        keys = list(param_grid.keys())
        values_list = [param_grid[k] for k in keys]

        # 2. DEAP Setup
        # We represent an individual as a list of INDICES into the values_list
        # This allows handling non-numeric parameters (strings, bools) uniformly.

        # Clean up previous DEAP types if they exist (to avoid conflicts on reload)
        if "FitnessMax" in creator.__dict__: del creator.FitnessMax
        if "Individual" in creator.__dict__: del creator.Individual

        creator.create("FitnessMax", base.Fitness, weights=(1.0,)) # Maximize target metric
        creator.create("Individual", list, fitness=creator.FitnessMax)

        toolbox = base.Toolbox()

        # Attribute generator: Random integer for each parameter index
        toolbox.register("attr_int", random.randint, 0, 0) # Placeholder range

        # Structure initializers
        # We need a custom init that respects the length of each param list
        def init_individual(icls):
            genome = []
            for v_list in values_list:
                genome.append(random.randint(0, len(v_list) - 1))
            return icls(genome)

        toolbox.register("individual", init_individual, creator.Individual)
        toolbox.register("population", tools.initRepeat, list, toolbox.individual)

        # Evaluation Function
        def evaluate(individual):
            # Decode indices to actual params
            params = {}
            for i, idx in enumerate(individual):
                # Clamp index just in case mutation goes out of bounds
                valid_idx = max(0, min(idx, len(values_list[i]) - 1))
                params[keys[i]] = values_list[i][valid_idx]

            try:
                # print(f"Evaluating: {params}")
                try:
                    strategy_instance = StrategyClass(parameters=params)
                except TypeError:
                     strategy_instance = StrategyClass()
                     if hasattr(strategy_instance, 'set_parameters'):
                         strategy_instance.set_parameters(params)

                res = engine._execute_fast(df, strategy_instance, precalc_arrays=precalc_arrays)
                metric_val = res['metrics'].get(target_metric, -float('inf'))

                # Penalize low trade count? (Optional)
                if res['metrics'].get('total_trades', 0) < 5:
                    metric_val = -float('inf') # Avoid overfitting on lucky few trades

                return (metric_val,)
            except Exception:
                return (-float('inf'),)

        toolbox.register("evaluate", evaluate)

        # Genetic Operators
        # Crossover: TwoPoint
        toolbox.register("mate", tools.cxTwoPoint)

        # Mutation: Uniform Integer Mutation
        # Mutate each gene with probability `indpb` to a new int within range
        def mutate(individual, indpb):
            for i in range(len(individual)):
                if random.random() < indpb:
                    # New random index
                    individual[i] = random.randint(0, len(values_list[i]) - 1)
            return (individual,)

        toolbox.register("mutate", mutate, indpb=0.2)

        # Selection: Tournament
        toolbox.register("select", tools.selTournament, tournsize=3)

        # 3. Run GA
        pop = toolbox.population(n=population_size)
        hof = tools.HallOfFame(10) # Keep top 10

        # Use simple EA
        # We can use parallel map?
        # toolbox.register("map", futures.map) # If we want parallelism

        # For simplicity, sequential for now or basic map
        # With Numba, sequential evaluation of 50 pop * 10 gen = 500 runs takes ~5s. Parallel might be overkill for setup cost.
        # But let's try to be fancy.
        # stats = tools.Statistics(lambda ind: ind.fitness.values)
        # stats.register("avg", np.mean)
        # stats.register("max", np.max)

        final_pop, log = algorithms.eaSimple(pop, toolbox, cxpb=0.5, mutpb=0.2, ngen=generations,
                                           stats=None, halloffame=hof, verbose=True)

        # 4. Format Results
        top_results = []
        for ind in hof:
            params = {}
            for i, idx in enumerate(ind):
                 valid_idx = max(0, min(idx, len(values_list[i]) - 1))
                 params[keys[i]] = values_list[i][valid_idx]

            score = ind.fitness.values[0]
            top_results.append({
                "params": params,
                "score": score
            })

        best = top_results[0]

        # Re-run best to get full metrics
        # (Since evaluate returns only fitness tuple)
        # Actually, we could store full metrics in individual attributes but cleaner to re-run one fast test.
        try:
            strategy_instance = StrategyClass(parameters=best['params'])
        except TypeError:
            strategy_instance = StrategyClass()
            strategy_instance.set_parameters(best['params'])
        res = engine._execute_fast(df, strategy_instance, precalc_arrays=precalc_arrays)
        best_metrics = res['metrics']

        return {
            "strategy": strategy_name,
            "dataset_id": dataset_id,
            "method": "Genetic Algorithm",
            "best_params": best['params'],
            "best_metrics": best_metrics,
            "top_10": top_results,
            "generations": generations,
            "population_size": population_size
        }

    except Exception as e:
        logger.error(f"Genetic Optimization failed: {e}")
        raise OptimizationError(f"Genetic Optimization failed: {str(e)}")
