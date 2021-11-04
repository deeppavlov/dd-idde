# DD-IDDE: Design Discourse-Driven Open-Domain Chatbots


[![](https://img.shields.io/twitter/follow/deeppavlov.svg?style=social)](https://twitter.com/intent/follow?screen_name=deeppavlov)

This extension enables developers of the open-domain chatbots with an option to design them within VS Code using customized Draw.io UI and **Discourse Moves Recommendations** to make dialog more smooth and natural.

This extension uses DeepPavlov's [Dialog Flow Framework](https://github.com/deepmipt/dialog_flow_framework) as the runtime environment for the open-domain chatbots. It also uses [DD-IDDE SDK](https://github.com/deepmipt/dd_idde_sdk) that enables the use of the Discourse Moves recommendations during the design phase as well in the runtime.

**Discourse Moves Recommendation System** has been built based on the Discourse & Speech Functions theory originally created by M.A.K. Halliday and further developed by Eggins & Slade in their book ["Analysing Casual Conversation"](https://www.equinoxpub.com/home/analysing-casual-conversation-suzanne-eggins-diana-slade/).

This extension is built on top of the unnoficial integration of the [Draw.io](https://app.diagrams.net/) (also known as [diagrams.net](diagrams.net)) into VS Code made by Henning Dieterichs, [hediet](https://github.com/hediet) on Github (Main Contributor / Author).

## Features

-   Open ```.py``` files representing dialog flows of the open-domain chatbots using the Draw.io editor.
    -   To create a new dialog flow, simply copy an example file from examples folder, right click on the file, choose "Open With", and select "DD-IDDE" diagram, simply create an empty `*.drawio`, `*.drawio.svg` or `*.drawio.png` file and open it.
-   Uses an offline version of Draw.io by default.

## Demo

TBD

## Prerequisites
### Environment

| Item           | Requirements                                          | Comments                                                     |
| -------------- | ----------------------------------------------------- | ------------------------------------------------------------ |
| OS             | Debian-based distribution, e.g., Ubuntu or Windows 10 | This version was tested on Ubuntu 18.04 under WSL2 on Windows 11 and Windows 10. |
| Python         | v3.9+                                                 | This version was tested on OS with Python 3.9.               |
| Docker         | v20+                                                  | This version was tested with Docker v20.10.7 (64-bit).       |
| Docker-Compose | v1.29.2                                               | This version was tested with Docker-Compose v1.29.2.         |

### Python Modules

| Item | Requirements | Comments                                  |
| ---- | ------------ | ----------------------------------------- |
| lxml | v4.6.3       | This version was tested with lxml v4.6.3. |

### DD-IDDE SDK Installation

1. Clone SDK: ```git clone https://github.com/deepmipt/dd_idde_sdk```
2. Change to its directory: ```cd dd_idde_sdk```
3. Install requirements: ```pip3 install -r requirements.txt```

### DD-IDDE SDK Runtime

1. Run DD-IDDE SDK Runtime with Docker-Compose: ```docker-compose up --build```

## Design & Run Your Open-Domain/Scenario-Driven Chatbot in DD-IDDE
### Start With The Built-In Example
1. Open VS Code in your ```dd_idde_sdk``` folder by running ```code .```.
2. Go to ```experiments``` folder.
3. Open ```example_1_basics.py```.
3. Right click on ```example_1_basics.py```, choose "Open with...", and in the dialog box choose "DD-IDDE Dialog Designer".
### Use Discourse Moves Recommendation System
1. In Draw.io designer tab in VS Code, click on the node, e.g., ```start_node```, then click on ```Show Suggestions``` menu item. If nothing shows up click again.
2. Pick the suggestion based on the Speech Function you want to add support for.
3. Double click on that suggestion. You can specify the speech function of your target response if you like, or you can do that later, either in code or from the Draw.io Dialog Designer.
### Run
Once you've designed your Discourse-Driven open-domain chatbot, you can run it:
1. Open Terminal in the ```dd_idde_sdk``` folder.
2. Run ```python3 experiments/example_1_basics.py```.
3. Type your response. If you didn't edit the file, you can type "How are you?" or "How are you doing?". If DD-IDDE SDK Runtime is running (in Docker), you should see debug output from the system that says how your utterance was classified by the Speech Function classifier, and the system will provide the response based on the transition conditioned by the "Open.Demand.Fact" Speech Function from the ```start_node``` to the corresponding node in the ```example_1_basics.py``` file. 

## Themes

<details>
    <summary><b>Available Draw.io Themes</b></summary>
    <!-- Please use HTML syntax here so that it works for Github and mkdocs -->
    <ul>
        <li><p>Theme "atlas"</p><img src="docs/theme-atlas.png" alt="atlas" width="800"></li>
        <li><p>Theme "Kennedy"</p><img src="docs/theme-Kennedy.png" alt="Kennedy" width="800"></li>
        <li><p>Theme "min"</p><img src="docs/theme-min.png" alt="min" width="800"</li>
        <li><p>Theme "dark"</p><img src="docs/theme-dark.png" alt="dark" width="800"></li>
    </ul>
</details>

## Editing the Dialog Designer and its DFF Python Side by Side

You can open the same `*.py` file with the Draw.io Dialog Designer and as `.py` file.
They are synchronized, so you can switch between them as you like it.
This is super pratical if you want to use find/replace to rename text or other features of VS Code to speed up your diagram creation/edit process.
Use the `View: Reopen Editor With...` command to toggle between the text or the Draw.io-based **DD-IDDE Dialog Designer** editor. You can open multiple editors for the same file.

## DD-IDDE Contributors

-   Oleg Serikov, [oserikov](https://github.com/oserikov) on Github (Original Author)
-   Bálint Magyar, [mablin7](https://github.com/mablin7) on Github (Frontend Software Engineer)
-   Dmitry Babadeev, [prog420](https://github.com/prog420) on Github (Main Contributor in August-October 2021)
-   Denis Kuznetsov, [kudep](https://github.com/kudep) on Github (Author of DD-IDDE SDK & Dialog Flow Framework/DFF)
-   Lida Ostyakova, [lnpetrova](https://github.com/lnpetrova) on Github (Author of Discourse Moves Recommendation System)
-   Dmitry Evseev, [dmitrijeuseew](https://github.com/dmitrijeuseew) on Github (Author of Wiki-based entity detection extensions for DFF)
-   Daniel Kornev, [DanielKornev](https://github.com/DanielKornev) on Github (PM)

## Original Draw.io Extension Contributors

-   Henning Dieterichs, [hediet](https://github.com/hediet) on Github (Main Contributor / Author)
-   Vincent Rouillé, [Speedy37](https://github.com/Speedy37) on Github

## See Also / Similar Extensions

-   [Draw.io](https://app.diagrams.net/) - This extension relies on the giant work of Draw.io. Their embedding feature enables this extension! This extension bundles a recent version of Draw.io.
-   [vscode-drawio](https://github.com/eightHundreds/vscode-drawio) by eightHundreds.

## Other Cool Conversational AI Tech by DeepPavlov

If you like this extension, you might like [our other Conversational AI tech](https://deeppavlov.ai) too:

-   **[DeepPavlov Library](https://www.github.com/deepmipt/deeppavlov)**: An open-source Conversational AI library (Python, TF 1.x, PyTorch).
-   **[DeepPavlov Dream](https://www.github.com/deepmipt/dream)**: An open-source Multiskill AI Assistant Platform.
-   **[DeepPavlov Agent](https://www.github.com/deepmipt/dp-agent)**: An open-source Conversational AI orchestrator (it used by DeepPavlov Dream).
