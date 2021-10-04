flows = {
    GLOBAL: {
        TRANSITIONS: {},
        PROCESSING: {},
        RESPONSE: {},
    },
    "greeting_flow": {
        'start_node': {
            TRANSITIONS: {'node2': "Hi there!"},
            PROCESSING: {3: [preproc1, preproc2]},
            RESPONSE: ""
        },
        'node2': {
            TRANSITIONS: {'start_node': "Hi ther!"},
            PROCESSING: {3: [preproc1, preproc2]},
            RESPONSE: ""
        }
    }
}
