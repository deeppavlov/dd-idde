import logging
from typing import Optional, Union

from dff.core.keywords import TRANSITIONS, RESPONSE
from dff.core import Context, Actor
import dff.conditions as cnd

logger = logging.getLogger(__name__)

# First of all, to create a dialog agent, we need to create a dialog script.
# Below, `flows` is the dialog script.
# A dialog script is a flow dictionary that can contain multiple flows .
# Flows are needed in order to divide a dialog into sub-dialogs and process them separately.
# For example, the separation can be tied to the topic of the dialog.
# In our example, there is one flow called greeting_flow.

# Inside each flow, we can describe a sub-dialog using keyword `GRAPH` from dff.core.keywords module.
# Here we can also use keyword `GLOBAL_RESPONSE`, which we have considered in other examples.

# `GRAPH` describes a sub-dialog using linked nodes, each node has the keywords `RESPONSE` and `TRANSITIONS`.

# `RESPONSE` - contains the response that the dialog agent will return when transitioning to this node.
# `TRANSITIONS` - describes transitions from the current node to other nodes.
# `TRANSITIONS` are described in pairs:
#      - the node to which the agent will perform the transition
#      - the condition under which to make the transition


def preproc1(): pass
def preproc2(): pass
def preproc3(): pass
def preproc4(): pass
def preproc5(): pass


flows = {
    GLOBAL: {
        TRANSITIONS: {},
        PROCESSING: {},
        RESPONSE: {},
    },
    "greeting_flow": {
        'start_node': {
            TRANSITIONS: {'node3': "Hi there!"},
            PROCESSING: {3: [preproc1, preproc2]},
            RESPONSE: ""
        },
        'node1': {
            TRANSITIONS: {'node2': cnd.exact_match("i'm fine, how are you?")},
            PROCESSING: {},
            RESPONSE: "Hi, how are you?"
        },
        'node2': {
            TRANSITIONS: {'node3': cnd.exact_match()},
            PROCESSING: {},
            RESPONSE: "Good. What do you want to talk about?"
        },
        'node3': {
            TRANSITIONS: {'node4': cnd.exact_match("Ok, goodbye.")},
            PROCESSING: {},
            RESPONSE: "Sorry, I can not talk about music now."
        },
        'node4': {
            TRANSITIONS: {'node1': cnd.exact_match("Hi")},
            PROCESSING: {},
            RESPONSE: "bye"
        },
        'fallback_node': {
            TRANSITIONS: {'node1': cnd.exact_match("Hi")},
            PROCESSING: {},
            RESPONSE: "Ooops"
        }
    },
    "small_talk_flow": {
        'start_node': {
            TRANSITIONS: {'node1': "How are you!"},
            PROCESSING: {},
            RESPONSE: ""
        },
        'node1': {
            TRANSITIONS: {'node2': foo.bar("i'm fine, how are you?")},
            PROCESSING: {},
            RESPONSE: "Hi, how are you?"
        },
        'node2': {
            TRANSITIONS: {'node3': cnd.exact_match()},
            PROCESSING: {},
            RESPONSE: "Good. What do you want to talk about?"
        },
        'node3': {
            TRANSITIONS: {'node4': cnd.exact_match("Ok, goodbye.")},
            PROCESSING: {},
            RESPONSE: "Sorry, I can not talk about music now."
        },
        'node4': {
            TRANSITIONS: {'node1': cnd.exact_match("Hi")},
            PROCESSING: {},
            RESPONSE: "bye"
        },
        'fallback_node': {
            TRANSITIONS: {'node1': cnd.exact_match("Hi")},
            PROCESSING: {},
            RESPONSE: "Ooops"
        }
    },

}


# An actor is an object that processes user input replicas and returns responses
# To create the actor, you need to pass the script of the dialogue `flows`
# And pass the initial node `start_node_label`
# and the node to which the actor will go in case of an error `fallback_node_label`
# If `fallback_node_label` is not set, then its value becomes equal to `start_node_label` by default
actor = Actor(
    flows,
    start_node_label=("greeting_flow", "start_node"),
    fallback_node_label=("greeting_flow", "fallback_node"),
)


# turn_handler - a function is made for the convenience of working with an actor
def turn_handler(
    in_request: str,
    ctx: Union[Context, str, dict],
    actor: Actor,
    true_out_response: Optional[str] = None,
):
    # Context.cast - gets an object type of [Context, str, dict] returns an object type of Context
    ctx = Context.cast(ctx)
    # Add in current context a next request of user
    ctx.add_request(in_request)
    # pass the context into actor and it returns updated context with actor response
    ctx = actor(ctx)
    # get last actor response from the context
    out_response = ctx.last_response
    # the next condition branching needs for testing
    if true_out_response is not None and true_out_response != out_response:
        raise Exception(
            f"{in_request=} -> true_out_response != out_response: {true_out_response} != {out_response}")
    else:
        logging.info(f"{in_request=} -> {out_response}")
    return out_response, ctx


# testing
testing_dialog = [
    ("Hi", "Hi, how are you?"),  # start_node -> node1
    ("i'm fine, how are you?", "Good. What do you want to talk about?"),  # node1 -> node2
    # node2 -> node3
    ("Let's talk about music.", "Sorry, I can not talk about music now."),
    ("Ok, goodbye.", "bye"),  # node3 -> node4
    ("Hi", "Hi, how are you?"),  # node4 -> node1
    ("stop", "Ooops"),  # node1 -> fallback_node
    ("stop", "Ooops"),  # fallback_node -> fallback_node
    ("Hi", "Hi, how are you?"),  # fallback_node -> node1
    ("i'm fine, how are you?", "Good. What do you want to talk about?"),  # node1 -> node2
    # node2 -> node3
    ("Let's talk about music.", "Sorry, I can not talk about music now."),
    ("Ok, goodbye.", "bye"),  # node3 -> node4
]


def run_test():
    ctx = {}
    for in_request, true_out_response in testing_dialog:
        _, ctx = turn_handler(in_request, ctx, actor,
                              true_out_response=true_out_response)


# interactive mode
def run_interactive_mode(actor):
    ctx = {}
    while True:
        in_request = input("type your answer: ")
        _, ctx = turn_handler(in_request, ctx, actor)


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s-%(name)15s:%(lineno)3s:%(funcName)20s():%(levelname)s - %(message)s",
        level=logging.INFO,
    )
    run_test()
    run_interactive_mode(actor)
