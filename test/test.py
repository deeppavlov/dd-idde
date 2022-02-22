from dff.core.keywords import TRANSITIONS, RESPONSE, MISC, PROCESSING
from dff.core import Actor
import dff.conditions as cnd

plot = {
    "flow": {
        "start_node": {
            TRANSITIONS: {
                ("flow2", "suggestion"): cnd(
                    a_multiline_condition,
                    hello
                )
            },
            RESPONSE: "",
            MISC: {
                "speech_functions": ["React.Rejoinder.Support.Response.Resolve"],
            },
        },
    },
    "flow2": {
        "suggestion": {
            TRANSITIONS: {},
            RESPONSE: '',
            MISC: {"speech_functions": ["React.Rejoinder.Support.Response.Resolve"]}
        }
    }
}