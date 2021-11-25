from dff.core.keywords import TRANSITIONS, RESPONSE, MISC, PROCESSING
from dff.core import Actor
import dff.conditions as cnd

plot = {
    "flow": {
        "start_node": {
            TRANSITIONS: {("flow2", "fallback_node"): cnd},
            RESPONSE: "",
            MISC: {
                "speech_functions": ["React.Rejoinder.Support.Response.Resolve"],
            },
        },
    },
    "flow2": {
        "fallback_node": {
            TRANSITIONS: {"suggestion": dm_cnd.is_sf("React.Rejoinder.Support.Track.Clarify")},
            RESPONSE: "",
            MISC: {"speech_functions": ["Open.Demand.Opinion"]},
        },
        "suggestion": {
            TRANSITIONS: {},
            RESPONSE: '',
            MISC: {"speech_functions": ["React.Rejoinder.Support.Response.Resolve"]}
        }
    }
}