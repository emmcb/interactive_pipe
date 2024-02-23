from interactive_pipe import Control
from interactive_pipe.headless.pipeline import HeadlessPipeline
from interactive_pipe.graphical.qt_gui import InteractivePipeQT
from interactive_pipe import interactive
from interactive_pipe.data_objects.image import Image
from interactive_pipe.thirdparty.images_openai_api import ImageFromPrompt
from pathlib import Path
import cv2

root = Path(__file__).parent
img_folder = root/"images"
audio_folder = root/"audio"
TRACK = "track"
IMAGE = ICON = "image"
CAPTION = "caption"
PROMPT = "prompt"
PROMPT_STYLE = "a cute crayon drawing of "
PROMPT_EXTRA = " on a white background, using a style from a cartoon book for baby kids"

# Audio generated by https://huggingface.co/spaces/facebook/MusicGen
# Elephant : a short savanah jungle music like the lion's king akuna matata with elephants barking
# Snail: a short instrumental country song with banjo without lyrics
# Rabbit: we will rock you by queens but played with ukulele  without lyrics
TRACK_DICT = {
    "elephant": {
        TRACK: audio_folder/"elephant.mp4",
        CAPTION: "ELEPHANT",
        PROMPT: "a smiling elephant walking in the sunny yellow savana",
    },
    "snail": {
        TRACK: audio_folder/"snail.mp4",
        CAPTION: "SNAIL",
        PROMPT: "a cute yellow and orange snail with two eyes slowly walking on the green grass"
    },
    "rabbit": {
        TRACK: audio_folder/"rabbit.mp4",
        CAPTION: "RABBIT",
        PROMPT: "a smiling funny little rabbit in the green grass",
    },
    "pause": {
        TRACK: None,
        PROMPT: "a cute sleeping cat",
        CAPTION: "...zzzz"
    }
}

for item_name, element in TRACK_DICT.items():
    TRACK_DICT[item_name][IMAGE] = ImageFromPrompt.generate_image(
        PROMPT_STYLE + element[PROMPT] + PROMPT_EXTRA,
        img_folder/(item_name+".png"),
        size=(512, 512)
    )
ICONS = [it[ICON] for key, it in TRACK_DICT.items()]


@interactive(
    song=Control("elephant", list(TRACK_DICT.keys()), icons=ICONS)
)
def song_choice(global_params={}, song="elephant"):
    global_params[TRACK] = song
    first_exec = global_params.get("first_exec", True)
    if not first_exec:
        audio_track = TRACK_DICT[song][TRACK]
        if audio_track is None:
            global_params["__stop"]()
        else:
            global_params["__set_audio"](audio_track)
            global_params["__play"]()
    else:
        global_params["first_exec"] = False


def image_choice(global_params={}):
    song = global_params.get(TRACK, list(TRACK_DICT.keys())[0])
    img = Image.from_file(TRACK_DICT[song][IMAGE]).data
    max_height = 300  # Raspberry pi with a 7" touchscreen
    h, w, _c = img.shape
    if h > max_height:
        img = cv2.resize(img, (w*max_height//h, max_height))
        h, w, _c = img.shape
    caption = TRACK_DICT[song][CAPTION]
    global_params["__output_styles"]["img_out"] = {
        "title": caption
    }  # discard auto titling
    return img


def sample_pipeline():
    song_choice()
    img_out = image_choice()
    return img_out


if __name__ == '__main__':
    pip = HeadlessPipeline.from_function(sample_pipeline, cache=False)
    app = InteractivePipeQT(pipeline=pip, name="music", size=None, audio=True)
    app()
