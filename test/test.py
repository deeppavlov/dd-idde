from dff.core.keywords import TRANSITIONS, RESPONSE, MISC, PROCESSING
from dff.core import Actor
import dff.conditions as cnd

plot = {
    "flow": {
        "start_node": {
            TRANSITIONS: {
                "suggestionasd": lambda ctx, actor, *args, **kwargs: True,
                "suggestion011": dm_cnd.is_sf("yes_no_question")
            },
            RESPONSE: "",
            MISC: {
                "speech_functions": ["opinion"],
            },
        },
        "suggestion011": {
            RESPONSE: '',
            TRANSITIONS: {"suggestion": dm_cnd.is_midas("opinion")},
            MISC: {"dialog_act": "comment"},
        },
        "suggestion": {
            RESPONSE: '',
            TRANSITIONS: {},
            MISC: {"dialog_act": "opinion"},
        },
        "suggestionasd": {RESPONSE: '', TRANSITIONS: {}},
    }
}