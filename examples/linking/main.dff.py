import common.universal_templates as templates
import common.constants as common_constants
from dff import GRAPH, RESPONSE, TRANSITIONS, GLOBAL_TRANSITIONS, PROCESSING
from dff import previous, forward
from common.speech_functions.generic_responses import (
    sys_response_to_speech_function_request as generic_responses_intent,
)
from common.dialogflow_framework.extensions import intents, custom, custom_functions, priorities, generic_responses
from common.dialogflow_framework.extensions.facts_utils import fact_provider
from common.dialogflow_framework.extensions.custom_functions import set_confidence_and_continue_flag


flows = {
    "animals": {
        GRAPH: {
            "ask_some_questions": {
                RESPONSE: "todo",
                TRANSITIONS: {
                    "have_pets": custom_functions.speech_functions("Open.Give.Fact"),
                    "like_animals": custom_functions.speech_functions("Open.Attend"),
                },
                MISC: {"speech_functions": ["Open.Give.Opinion"]},
            },
            "have_pets": {
                RESPONSE: "todo",
                TRANSITIONS: {
                    "what_animal": custom_functions.speech_functions("Open.Attend")
                },
                MISC: {"speech_functions": ["Open.Demand.Opinion"]},
            },
            "like_animals": {
                RESPONSE: "todo",
                TRANSITIONS: {
                    "what_animal": custom_functions.speech_functions("Open.Attend"),
                    "smth_on_facts": custom_functions.speech_functions(
                        "Open.Demand.Fact"
                    ),
                },
                MISC: {"speech_functions": ["Open.Attend"]},
            },
            "what_animal": {
                RESPONSE: "todo",
                TRANSITIONS: {
                    "ask_about_color": custom_functions.speech_functions(
                        "React.Rejoinder.Support.Track.Check"
                    ),
                    "ask_about_breed": custom_functions.speech_functions("Open.Attend"),
                },
                MISC: {"speech_functions": ["Open.Attend"]},
            },
            "ask_about_color": {
                RESPONSE: "todo",
                TRANSITIONS: {},
                MISC: {"speech_functions": ["Open.Attend"]},
            },
            "ask_about_breed": {
                RESPONSE: "todo",
                TRANSITIONS: {
                    "tell_fact_about_breed": custom_functions.speech_functions(
                        "Open.Attend"
                    )
                },
                MISC: {"speech_functions": ["Open.Attend"]},
            },
            "tell_fact_about_breed": {
                RESPONSE: "todo",
                TRANSITIONS: {
                    "ask_about_training": custom_functions.speech_functions(
                        "React.Rejoinder.Support.Track.Probe"
                    )
                },
                MISC: {"speech_functions": ["React.Respond.Confront.Reply.Contradict"]},
            },
            "ask_about_training": {
                RESPONSE: "todo",
                TRANSITIONS: {},
                MISC: {"speech_functions": ["Open.Attend"]},
            },
            "smth_on_facts": {
                RESPONSE: "todo",
                TRANSITIONS: {},
                MISC: {
                    "speech_functions": ["React.Rejoinder.Support.Response.Resolve"]
                },
            },
        }
    },
    "generic_responses_default": generic_responses.create_new_flow(priority=0.9),
}
