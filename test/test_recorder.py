import numpy as np
import pytest
import shutil
from copy import deepcopy
from typing import List
from sample_functions import mad, split_horizontally, blend, get_sample_image, empty_output, constant_image_generator, empty_in_empty_out

try:
    from interactive_pipe.core.filter import FilterCore, PureFilter
    from interactive_pipe.core.engine import PipelineEngine
    from interactive_pipe.core.pipeline import PipelineCore
    from interactive_pipe.core.graph import get_call_graph
    from interactive_pipe.headless.pipeline import HeadlessPipeline
    from interactive_pipe.data_objects.image import Image
except:
    import helper
    from core.filter import FilterCore, PureFilter
    from core.engine import PipelineEngine
    from core.pipeline import PipelineCore
    from headless.pipeline import HeadlessPipeline
    from core.graph import get_call_graph
    from data_objects.image import Image

input_image = np.array([[1, 2, 3], [4, 5, 6]])



def pipe_func(img_a, img_b, param_1 = 0.8):
    blended = blend(img_a, img_b)
    exposed_img = mad(blended)
    final = blend(img_a, exposed_img)
    final_up, final_middle, final_down = split_horizontally(final,  line=0.8)
    empty_output(final_middle)
    uniform = constant_image_generator()
    empty_in_empty_out()
    return final_up, blended

def pipe_func_inplace(img_a, img_b, param_1 = 0.8):
    img_b = blend(img_a, img_b)
    img_b = mad(img_b)
    img_b = blend(img_a, img_b)
    img_b, final_middle, final_down = split_horizontally(img_b,  line=0.8)
    _unused, _unused_2, _unused_3 = split_horizontally(img_b,  line=0.8)
    return img_b, final_middle


def test_graph_retrieval():
    graph = get_call_graph(pipe_func)
    # print(graph)
    assert graph["function_name"] == pipe_func.__name__
    assert graph["returns"] == ["final_up", "blended"]
    assert graph["args"] == ["img_a", "img_b"]


@pytest.mark.parametrize("func", [pipe_func, pipe_func_inplace])
def test_headless_pipeline(tmp_path_factory, func):
    input_image = get_sample_image()
    pip = HeadlessPipeline.from_function(func, inputs=[input_image, 0.8*input_image])
    out_path = tmp_path_factory.mktemp("data_2")
    assert out_path.exists()
    pip.save(out_path/"_image.jpg", data_wrapper_fn=lambda x: Image(x))
    shutil.rmtree(out_path) # clean  temporary folder


def headless_pipeline_exec(func=pipe_func):
    input_image = get_sample_image()
    func(input_image, 0.8*input_image)
    pip = HeadlessPipeline.from_function(func, inputs=[input_image, 0.8*input_image])
    pip.run()

if __name__ == '__main__':
    headless_pipeline_exec()