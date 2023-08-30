# Concept
- Develop your algorithm while debugging with plots, while checking robustness & continuity to parameters change
- Tune your algorithms and save your parameters for later batch processing
- Ready to batch under the hood, the processing engine can be ran without GUI (therefore allowing to use the same code for tuning & batch processing if needed).


# Status
- :x: not on PyPi yet
- supported backends 
    - :ok: pyQt/pySide 
    - :hammer: matplotlib
    - :hammer: ipywidget for jupyter notebooks
- tested platforms
    - :ok: Linux (Ubuntu / KDE Neon)
    - :ok: RapsberryPi


# Short guide
Let's defne 3 image processing very basic filters `exposure`, `black_and_white` & `blend`.
By design:
- image buffers inputs are arguments
- parameters are keyword arguments
- output buffers are simply returned 

We'll decorate each image filter by providing some Controls which will allow creating a graphical interface.
`@interactive(param_1=Control(...), param_2=Control(...), ...)`

Finally, we need to the glue to combo these filters. This is where the sample_pipeline function comes in.
By decorating it with `@interactive_pipeline(gui="qt")`, calling this function will magically turn into a GUI powered image processing pipeline.

```python
from interactive_pipe.core.decorator import interactive, interactive_pipeline
from interactive_pipe.core.control import Control
import numpy as np


@interactive(
    coeff= Control(1., [0.5, 2.], name="exposure"),    # 1. is the default value, [0.5, 2.] is the range
    bias= Control(0., [-0.2, 0.2], name="offset expo") # 0. is the default value, [-0.2, 0.2] is the slider range
)
def exposure(img, coeff = 1., bias=0):
    '''Applies a multiplication by coeff & adds a constant bias to the image'''
    mad = img*coeff + bias
    return mad


@interactive(
    bnw = Control(True, name="Black and White") # booleans will allow adding a tickbox
)
def black_and_white(img, bnw=True):
    '''Averages the 3 color channels (Black & White) if bnw=True
    '''
    return np.repeat(np.expand_dims(np.average(img, axis=-1), -1), img.shape[-1], axis=-1) if bnw else img

@interactive(
    blend_coeff= Control(0.5, [0., 1.], name="blend coefficient"),
)
def blend(img0, img1, blend_coeff=0.): 
    # please note that blend_coeff=0. will be replaced by the default 0.5 Control value
    '''Blends between two image. 
    - when blend_coeff=0 -> image 0  [slider to the left ] 
    - when blend_coeff=1 -> image 1   [slider to the right] 
    '''
    blended = (1-blend_coeff)*img0+ blend_coeff*img1
    return blended

@interactive_pipeline(gui="qt")
def sample_pipeline(input_image):
    exposed = exposure(input_image)
    bnw_image = black_and_white(input_image)
    blended  = blend(exposed, bnw_image)
    return exposed, blended, bnw_image

if __name__ == '__main__':
    input_image = np.array([0., 0.5, 0.8])*np.ones((256, 512, 3))
    sample_pipeline(input_image)
```
This code shall display you a GUI with three images. The middle one is the result of the blend

In the following guide, y



### Step 1 : defining basic functions

In this first part, we'll define very simple image processing filter functions. 

These will be unrelated to interactivity or sliders or anything fancy here!

>The important point here is that if you build any library, **you may not want interactive_pipe to interfere with it or even be imported in you module**. Let's keep functions as what they are, clean and simple without a relationship to GUI or interactivity.


So let's define 3 very simple image processing functions: `exposure`, `black_and_white` & `blend`.




:eyeglasses: Note that the blend function will process two buffers (interactive pipe is a multi input/output processing framework, not just single image filters)

Let's create a first file `image_filters.py`
```python
import numpy as np

# Applies a multiplication by coeff & adds a constant bias to the image
def exposure(img, coeff = 1., bias=0):
    mad = coeff * img + bias
    return mad

# Averages the 3 color channels (Black & White) if bnw=True
def black_and_white(img, bnw=False):
    return np.repeat(np.expand_dims(np.average(img, axis=-1), -1), img.shape[-1], axis=-1) if bnw else img

# Blends between two images img0 & img1
# - when blend_coeff=0 -> image 0
# - when blend_coeff=1 -> image 1 
def blend(img0, img1, blend_coeff=0.):
    blended = (1-blend_coeff)*img0+ blend_coeff*img1
    return blended
```


We can define a pipeline to sequentially run these image processing filters.
- Let's correct image exposure on the input image.  `exposed = exposure(input_image)`
- Let's apply a black & white style effect to the input image `bnw = black_and_white(input_image)`
- Let's finally blend these 2 images (the correctly exposed image & the black and white image).

We can actually run this function and it won't actually do much as all parameters have been set to "do nothing".

Let's create another file `sample_pipeline.py`
```python
import numpy as np
from image_filters import exposure, black_and_white, blend
def sample_pipeline(input_image):
    exposed = exposure(input_image)
    bnw_image = black_and_white(input_image)
    blended  = blend(exposed, bnw_image)
    return exposed, blended, bnw_image

if __name__ == '__main__':
    input_image = np.array([0., 0.5, 0.8])*np.ones((1, 2, 3)) # (w=2 x h=1) blue image
    bnw, blended, exposed = sample_pipeline(input_image)
    print(f"{blended=}")
#blended=array([[[0. , 0.5, 0.8],
#        [0. , 0.5, 0.8]]])
```

> If we want to change the parameters manually, we'll have to provide each keyword parameter to each function and the code will be much more difficult to read unfortunately
:warning:  Let's simply not do that, jump to the next section to see how interactive pipe will help you
```python
# Do not do this! 
# The code gets ugly 
# One of the nice aspect of the interactive_pipe is that you won't have to repeat all these parameters
def ugly_verbose_pipeline(input_image, blend_coeff=0.5, bnw=True, coeff=0.8, bias=0.):
    exposed = exposure(input_image, coeff=coeff, bias=bias)
    bnw_image = black_and_white(input_image, bnw=bnw)
    blended  = blend(exposed, bnw_image, blend_coeff=blend_coeff)
    return exposed, blended, bnw_image
# Now you can tweak your parameters as much as you want...
bnw, blended, exposed = sample_pipeline(input_image, blend_coeff=0.8, coeff=0.7, bias=-0.1, bnw=True)
```

### Step 2 : headless pipeline

Creating a `pipeline` by decorating our `sample_pipeline` function.
```python
from interactive_pipe.core.decorator import pipeline
@pipeline
def sample_pipeline(input_image):
    exposed = exposure(input_image)
    bnw_image = black_and_white(input_image)
    blended  = blend(exposed, bnw_image)
    return exposed, blended, bnw_image
print(sample_pipeline)


# {
# exposure : {'coeff': 1.0, 'bias': 0},
# black_and_white : {'bnw': False},
# blend : {'blend_coeff': 0.0}
# }
```
You can see here that the pipeline has been analyzed, parameters have been understood.

The underlying graph can be shown: the pipeline is made of links between our 3 filter. Each filter's outputs are provided to the next filter's inputs and so on.

```python
print(sample_pipeline.filters)

# [exposure
# (0)->(1)
# , black_and_white
# (0)->(2)
# , blend
# (1,2)->(3)
# ]
```

So let's simply run the function again like you'd classically do.
```python
input_image = np.array([0., 0.5, 0.8])*np.ones((1, 1, 3))
exposed, blended, bnw_image = sample_pipeline(input_image)
print(blended)
# [[[0.  0.5 0.8]]]
```

:fire: Now come some handy features of the `interactive_pipe`. *(you have to remember the ugly `ugly_verbose_pipeline` where all parameters had to be repeated manually.)*
```python
exposed, blended, bnw_image = sample_pipeline(input_image, bnw=True, blend_coeff=0.5)
print(bnw_image, blended)
# [[[0.43333333 0.43333333 0.43333333]]] [[[0.21666667 0.46666667 0.61666667]]]
```
```python
sample_pipeline.export_tuning("my_tuning.yaml")
```

Here's what `my_tuning.yaml` looks like.

```yaml 
black_and_white:
  bnw: true
blend:
  blend_coeff: 0.5
exposure:
  bias: 0
  coeff: 1.0
```

So obviously, you can modify this file & reload it `sample_pipeline.load_tuning()`. Internal parameters will be updated seamlessly so you can run your pipeline again.


### Step 3 : adding interactivity
Let's simply decorate some more functions in `sample_pipeline.py`
```python

import numpy as np
from image_filters import exposure, black_and_white, blend
from interactive_pipe.core.decorator import interactive, interactive_pipeline

# Let's make each of the three library filters interactive.
# Please note that image_filters.py was kept the same since the begining and does not depend on interactive_pipe
interactive(
    coeff= Control(1., [0.5, 2.], name="exposure"),
    bias= Control(0, [-0.2, 0.2], name="offset expo")
)(exposure)

interactive(
    bnw = Control(False, name="Black and White")
)(black_and_white)

interactive(
    blend_coeff= Control(0., [0., 1.], name="blend coefficient")
)(blend)

# Now let's decorate the sample pipeline with a specific GUI
@interactive_pipeline(gui="qt")
def sample_pipeline(input_image):
    exposed = exposure(input_image)
    bnw_image = black_and_white(input_image)
    blended  = blend(exposed, bnw_image)
    return exposed, blended, bnw_image

input_image = np.array([0., 0.5, 0.8])*np.ones((512, 256, 3))
sample_pipeline(input_image)
```
You should see a GUI pop now!

