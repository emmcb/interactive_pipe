import logging
from pathlib import Path
from typing import Any, Optional, Callable
from interactive_pipe.core.filter import FilterCore

from interactive_pipe.core.pipeline import PipelineCore
from interactive_pipe.data_objects.parameters import Parameters
from interactive_pipe.core.graph import get_call_graph
from interactive_pipe.core.filter import analyze_apply_fn_signature
from interactive_pipe.core.control import Control

class HeadlessPipeline(PipelineCore):
    """Adds some useful I/O to the pipeline core such as
    - importing/exporting tuning
    - printing current parameters in the terminal
    """
    @staticmethod
    def routing_indexes(inputs_names, all_variables):
        if inputs_names:
            inputs = []
            for input_index, input_name in enumerate(inputs_names):
                inputs.append(all_variables[input_name])
            if len(inputs) == 0:
                inputs = None
        else:
            inputs = None
        return inputs
    @classmethod
    def from_function(cls, pipe: Callable, inputs=None, **kwargs):
        assert isinstance(pipe, Callable)
        graph = get_call_graph(pipe)
        all_variables = {}
        total_index = 0
        function_inputs = {}
        for input_index, input_name in enumerate(graph["args"]):
            all_variables[input_name] = total_index
            function_inputs[input_name] = total_index
            total_index+= 1
        for filt_dict in graph["call_graph"]:
            for key in ["args", "returns"]:
                if filt_dict[key]:
                    for _, input_name in enumerate(filt_dict[key]):
                        if not input_name in all_variables.keys():
                            all_variables[input_name] = total_index
                            total_index+=1
        
        filters = []
        filters_count = {}
        filters_names = []
        control_list = []
        for filt_dict in graph["call_graph"]:
            # avoid duplicate filters names
            filt_name = filt_dict["function_name"]
            filter_count = filters_count.get(filt_name, -1)
            if filter_count >= 0:
                filters_count[filt_name]+= 1
                filt_name = filt_name + f"_{filters_count[filt_name]}"
            else:
                filters_count[filt_name] = 0
            inputs_filt = HeadlessPipeline.routing_indexes(filt_dict["args"], all_variables)
            outputs_filt = HeadlessPipeline.routing_indexes(filt_dict["returns"], all_variables)
            logging.debug("----------------->", filt_name, inputs_filt, outputs_filt)
            filter = FilterCore(
                name=filt_name,
                inputs=inputs_filt,
                outputs = outputs_filt,
                apply_fn=filt_dict["function_object"],
            )
            func_kwargs = analyze_apply_fn_signature(filt_dict["function_object"])[1]
            params_to_analyze = {**func_kwargs, **Control.get_controls(filt_name)}
            for param_name, param_value in params_to_analyze.items():
                if isinstance(param_value, Control):
                    param_value.connect_filter(filter, param_name)
                    filter.values = {param_name: param_value.value_default}
                    control_list.append(param_value)
            filters.append(filter)
            filters_names.append(filt_name)
        logging.debug(filters_count)
        logging.debug(filters_names)
        outputs = [all_variables[output_name] for output_name in graph["returns"]]
        if len(function_inputs) == 0 and inputs is None:
            logging.info("Auto deduced that there are no arguments provided to the function")
            inputs = []
        data_class = cls(filters=filters, name=graph["function_name"], inputs=inputs, outputs=outputs, **kwargs)
        data_class.controls = control_list
        return data_class
    
    def export_tuning(self, path: Optional[Path] = None, override=False) -> None:
        """Export yaml tuning to disk 
        """
        export_dict = {}
        for sl in self.filters:
            export_dict[sl.name] = sl.values
        saved_dict = export_dict
        if self.parameters != {}:
            # Legacy yaml generation to add more elements to reproduce
            if "path" in self.parameters:
                saved_dict["path"] = self.parameters["path"]
            if "tuning" in self.parameters:
                for elt in self.parameters["tuning"]:
                    if type(self.parameters["tuning"][elt]) == dict:
                        saved_dict[elt] = {}
                        for e in self.parameters["tuning"][elt]:
                            data = self.parameters["tuning"][elt][e][0]
                            index = int(self.parameters["tuning"][elt][e][1])
                            saved_dict[elt][e] = export_dict[data][index]
                    else:
                        data = self.parameters["tuning"][elt][0]
                        index = int(self.parameters["tuning"][elt][1])
                        saved_dict[elt] = export_dict[data][index]
        Parameters(saved_dict).save(path, override=True if path is None else override)
       

    def import_tuning(self, path: Path = None) -> None:
        """Open a yaml tuning and apply to GUI
        """
        # TODO: inform an update of parameters
        self.parameters = Parameters.load_from_file(path)

    def __repr__(self):
        """Print tuning parameters
        """
        ret = "\n{\n"
        for sl in self.filters:
            # ret += "\"%s\"" % sl.name + \
            #     ":[" + ",".join(map(lambda x: "%f" % x, sl.values)) + "],\n"
            ret += f"{sl.name} : {sl.values},\n"
        ret = ret[:-2] + "\n"  # remove comma for yaml
        ret += "}"
        return ret
    
    def __run(self):
        result_full = super().run()
        if self.outputs is not None:
            output_indexes = self.outputs
        else:
            output_indexes = self.filters[-1].outputs
        if output_indexes:
            if isinstance(output_indexes[0], list):
                return [[None if out_index is None else result_full[out_index] for idx, out_index in enumerate(row)] for idy, row in enumerate(output_indexes)]
            return tuple(result_full[idx] for idx in output_indexes)
        else:
            return None
    
    def run(self):
        self.results = self.__run()
        return self.results

    def save(self, path: Path = None, data_wrapper_fn: Callable = None, output_indexes: list = None, save_entire_buffer=False) -> Path:
        """Save full resolution image
        """
        if output_indexes is None:
            if self.outputs is not None:
                output_indexes = self.outputs
            else:
                output_indexes = self.filters[-1].outputs
        if save_entire_buffer:
            output_indexes = None # you may force specific buffer index you'd like to save
        result_full = super().run()
        if result_full is None:
            return None
        if not isinstance(path, Path):
            path = Path(path)
        self.export_tuning(path.with_suffix(".yaml"))
        assert isinstance(result_full, dict)
        for num, res_current in result_full.items():
            if output_indexes is not None and not num in output_indexes:
                continue
            current_name = path.with_name(
                path.stem + "_" + str(num) + path.suffix)
            if res_current is not None and not (isinstance(res_current, list) and len(res_current) == 0):
                if data_wrapper_fn is not None:
                    data_wrapper_fn(res_current).save(current_name)
                else:
                    assert hasattr(res_current, "save")
                    res_current.save(current_name)
            # @ TODO: handle proper output suffixes namings
            logging.info("saved image %s" % current_name)
        return path

    def parameters_from_keyword_args(self, **kwargs) -> dict:
        new_param_dict = {}
        for key, value in kwargs.items():
            for filter_name, parameters_dict in self.parameters.items():
                parameter_names = parameters_dict.keys()
                if key in parameter_names:
                    if not filter_name in new_param_dict.keys():
                        new_param_dict[filter_name] = {}
                    new_param_dict[filter_name][key] = value
        return new_param_dict


    def __call__(self, *inputs, parameters={}, **kwargs) -> Any:
        # @TODO: we could check that the number of inputs matches what's expected here.
        self.inputs = list(inputs)
        if len(self.inputs) == 0:
            self.inputs = None
        self.parameters = parameters
        self.parameters = self.parameters_from_keyword_args(**kwargs)
        return self.run()