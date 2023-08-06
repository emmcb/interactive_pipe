import logging
import sys
import time
import traceback
from copy import deepcopy
from typing import Dict, List, Optional, Callable, Tuple
from core.sliders import Slider
import inspect
from core.cache import CachedResults
from core.filter import FilterCore

class PipelineEngine:
    def __init__(self, cache=False, safe_input_buffer_deepcopy=True) -> None:
        self.cache = cache
        self.safe_input_buffer_deepcopy = safe_input_buffer_deepcopy

    def run(self, filters: List[FilterCore], imglst=None):
        performances = []
        logging.debug(100 * "-")
        if self.safe_input_buffer_deepcopy:
            # Want to be safe when there's no cache? always keep the input buffers of the first filter untouched
            logging.debug(f"<<< Deepcopy input images ")
            result = deepcopy(imglst)
        else:
            result = imglst
        skip_calculation = True
        previous_calculation = False
        for idx, prc in enumerate(filters):
            tic = time.perf_counter()
            # if cache not available or if cache available and values have changed, need to recalculate from now on
            # cache | has changed | skip_calculation
            # 0     | X           | False -> no cache, cannot skip so calculate
            # 1     | 0           | True -> cache with no change, skip the calculation
            # 1     | 1           | False -> cache and result changed, cannot skip so calculate
            skip_calculation &= (prc.cache_mem is not None) and (
                not prc.cache_mem.has_changed(prc.values))

            if skip_calculation and self.cache:
                logging.debug(
                    f"-->  Load cached outputs from filter {idx}: {prc.name}")
                out = prc.cache_mem.result
                previous_calculation = False
            else:
                logging.debug(
                    ("... " if previous_calculation else "!!! ") + f"Calculating {prc.name}")
                try:
                    routing_in = []
                    if prc.inputs:
                        routing_in = [
                            result[idi] if idi is not None else None for idi in prc.inputs]
                    logging.debug("in types->", [type(inp) for inp in routing_in])
                    out = prc.run(*routing_in)
                    logging.debug("out types->", [type(ou) for ou in out])
                except Exception as e:
                    logging.error(f'Error in {prc.name} filter:')
                    logging.error(e)
                    traceback.print_exc()
                    sys.exit(1)
                previous_calculation = True
                if self.cache and prc.cache_mem is not None:  # cache result if cache available
                    logging.debug(f"<-- Storing result from {prc.name}")
                    prc.cache_mem.update(out)
            # TODO: use str keys & dict for routing mechanism
            # put prc output at the right position within result vector
            if prc.outputs is not None:
                for i, ido in enumerate(prc.outputs):
                    if ido >= len(result): # need to extend the array with empty lists
                        for _j in range(0, ido - len(result) + 1):
                            result.append([])
                    if isinstance(out, list) or isinstance(out, tuple):
                        result[ido] = out[i]
                    # Simpler manner of defining a process fuction (do not return a list)
                    else:
                        result[ido] = out
            toc = time.perf_counter()
            performances.append(f"{prc.name}: {toc - tic:0.4f} seconds")

        # Limit result using self.numfigs but with indices pointed by last filter
        logging.info("\n".join(performances))
        logging.info(f"Full buffer: {len(result)}")
        return result