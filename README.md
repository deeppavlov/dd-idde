# DF Designer: Design Discourse-Driven Open-Domain Chatbots with DeepPavlov Conversational AI technologies


[![](https://img.shields.io/twitter/follow/deeppavlov.svg?style=social)](https://twitter.com/intent/follow?screen_name=deeppavlov)

This extension (previously known as DD-IDDE) enables developers of the open-domain chatbots with an option to design them within VS Code using customized Draw.io UI and **Discourse Moves Recommendations** to make dialog more smooth and natural.

This extension uses DeepPavlov's [Dialog Flow Framework](https://github.com/deepmipt/dialog_flow_framework) as the runtime environment for the open-domain chatbots. It can be used to build simple chatbots using [DF SDK](https://github.com/deepmipt/dialog_flow_sdk) or to build complex multi-skill AI Assistants using our [DeepPavlov Dream](https://github.com/deepmipt/dream) platform. 

**Discourse Moves Recommendation System** has been built based on the Discourse & Speech Functions theory originally created by M.A.K. Halliday and further developed by Eggins & Slade in their book ["Analysing Casual Conversation"](https://www.equinoxpub.com/home/analysing-casual-conversation-suzanne-eggins-diana-slade/).

This extension is built on top of the unnoficial integration of the [Draw.io](https://app.diagrams.net/) (also known as [diagrams.net](diagrams.net)) into VS Code made by Henning Dieterichs, [hediet](https://github.com/hediet) on Github (Main Contributor / Author).

## Features

-   Open ```.py``` files representing dialog flows of the open-domain chatbots using the Draw.io editor.
    -   To create a new dialog flow, simply copy an example file from examples folder, right click on the file, choose "Open With", and select "DF Designer".
-   Uses an offline version of Draw.io by default.

## Tutorials
### English
Stay tuned for a demo!

### Russian
Here's a recording of [introduction to DFF & DF Designer](https://www.youtube.com/watch?v=lNTu1QMB0XI) we've made back in the end of December. 

The image link below leads directly to the introduction of the **DF Designer** itself:

[![Introducing DF Designer](https://img.youtube.com/vi/lNTu1QMB0XI/1.jpg)](https://www.youtube.com/watch?v=lNTu1QMB0XI?t=2268 "Introducing DF Designer")

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

## Build Simple Chatbots with DF SDK
### DF SDK Installation

1. Clone SDK: ```git clone https://github.com/deepmipt/dialog_flow_sdk```
2. Change to its directory: ```cd dialog_flow_sdk```
3. Install requirements: ```pip3 install -r requirements.txt```

### DF SDK Runtime

1. Run DF SDK Runtime with Docker-Compose: ```docker-compose up --build```

### Design & Run Your Open-Domain/Scenario-Driven Chatbot in DF Designer

*NOTE: By default, the extension uses an SFC predictor running in the cloud, so you do not need to have the SDK running locally for predictions to work. You can still use a local predictor by changing the `sfc-predictor-url` in VS Code settings.*

### Start With The Built-In Example
1. Open VS Code in your ```dialog_flow_sdk``` folder by running ```code .```.
2. Go to ```examples``` folder.
3. Open ```food.py```.
3. Right click on ```food.py```, choose "Open with...", and in the dialog box choose "DD-IDDE Dialog Designer".

### Use Discourse Moves Recommendation System
1. In Draw.io designer tab in VS Code, double click on the node, e.g., ```start_node```, then choose a speech function from the list and click on ```save```. Now you can click on the node again and click on ```Show Suggestions``` menu item. If nothing shows up click again.
2. Pick the suggestion based on the Speech Function you want to add support for.
3. Double click on that suggestion. You can specify the speech function of your target response if you like, or you can do that later, either in code or from the Draw.io Dialog Designer.

### Run
Once you've designed your Discourse-Driven open-domain chatbot, you can run it:
1. Open Terminal in the ```dialog_flow_sdk``` folder.
2. Run ```python3 examples/food.py```.
3. If you didn't edit the file, you can type “Hi” to begin the dialog. The system then will ask you a question. Give any answer you want. If DF SDK Runtime is running (in Docker), you should see debug output from the system that says how your utterance was classified by the Speech Function classifier, and the system will provide the response based on the transition conditioned by the Speech Function of your response from the start_node to the corresponding node in the food.py file.

## Build Complex Multi-Skill AI Assistants with DeepPavlov Dream
### DeepPavlov Dream Installation

1. Clone Dream: ```git clone https://github.com/deepmipt/dream```
2. Change to its directory: ```cd dream```

*NOTE: By default, the extension uses an SFC predictor running in the cloud, so you do not need to have the SDK running locally for predictions to work. You can still use a local predictor by changing the `sfc-predictor-url` in VS Code settings.*

### Prepare Dream to Run Built-In Example Locally
1. Create `local.yml`: 
```
python3 utils/create_local_yml.py -p -d assistant_dists/dream_sfc/ -s dff-book-sfc-skill
```

### Design & Run Your Open-Domain/Scenario-Driven Skill in DF Designer

#### Start With The Built-In Example
1. Open VS Code in your ```https://github.com/deepmipt/dream/blob/main/skills/dff_book_sfc_skill/``` folder by running ```code .```.
2. Go to ```scenario``` folder.
3. Open ```main.py```.
3. Right click on ```main.py```, choose "Open with...", and in the dialog box choose "DF Dialog Designer".

### Use Discourse Moves Recommendation System
#### Pre-Requisites (needed in your custom skill, e.g., dff_template_skill)
To use Discourse Moves Recommendation System using Speech Functions you need to add integration with Speech Functions classifier:
1. Copy ```https://github.com/deepmipt/dream/blob/main/skills/dff_book_sfc_skill/scenario/sf_conditions.py``` next to ```main.py``` in the ```scenario``` folder of your ```dff_template_skill```.
2. Add line ```import scenario.sf_conditions as dm_cnd``` to your main.py file after ```line 14```.

#### Using Recommendations in Dialogue Design
1. In Draw.io designer tab in VS Code, double click on the node, e.g., ```start_node```, then choose a speech function from the list and click on ```save```. Now you can click on the node again and click on ```Show Suggestions``` menu item. If nothing shows up click again.
2. Pick the suggestion based on the Speech Function you want to add support for.
3. Double click on that suggestion. You can specify the speech function of your target response if you like, or you can do that later, either in code or from the Draw.io Dialog Designer.

### Run
Once you've designed your Discourse-Driven open-domain chatbot, you can run it:
1. Open Terminal in the ```dream``` folder.
2. Run ```docker-compose -f docker-compose.yml -f assistant_dists/dream_sfc/docker-compose.override.yml -f assistant_dists/dream_sfc/dev.yml -f assistant_dists/dream_sfc/local.yml up --build```.
3. In a separate Terminal tab run: ```docker-compose exec agent python -m deeppavlov_agent.run```. Type your response. If you didn't edit the file, you can type "How are you?" or "How are you doing?". If your custom Dream distribution is running (in Docker), you should see debug output from the system that says how your utterance was classified by the Speech Function classifier, and the system will provide the response based on the transition conditioned by the "Open.Demand.Fact" Speech Function from the ```start_node``` to the corresponding node in the ```example_1_basics.py``` file. 
4. Alternatively, can talk directly via REST API. Go to localhost:4242 and send POST requests like this:
```
{
	"user_id": "MyDearFriend",
	"payload": "hi how are you"
}
```

## Editing the Dialog Designer and its DFF Python Side by Side

You can open the same `*.py` file with the Draw.io Dialog Designer and as `.py` file.
They are synchronized, so you can switch between them as you like it.
This is super pratical if you want to use find/replace to rename text or other features of VS Code to speed up your diagram creation/edit process.
Use the `View: Reopen Editor With...` command to toggle between the text or the Draw.io-based **DD-IDDE Dialog Designer** editor. You can open multiple editors for the same file.

## DF Designer Contributors

-   Oleg Serikov, [oserikov](https://github.com/oserikov) on Github (Original Author)
-   Bálint Magyar, [mablin7](https://github.com/mablin7) on Github (Frontend Software Engineer)
-   Dmitry Babadeev, [prog420](https://github.com/prog420) on Github (Main Contributor in August-October 2021)
-   Denis Kuznetsov, [kudep](https://github.com/kudep) on Github (Author of DD-IDDE SDK & Dialog Flow Framework/DFF)
-   Lida Ostyakova, [lnpetrova](https://github.com/lnpetrova) on Github (Author of Discourse Moves Recommendation System)
-   Dmitry Evseev, [dmitrijeuseew](https://github.com/dmitrijeuseew) on Github (Author of Wiki-based entity detection extensions for DFF)
-   Kseniya Petukhova, [Kpetyxova](https://github.com/Kpetyxova) on GitHub (Developer & Tester of SFC-enabled skills)
-   Veronika Smilga, [NikaSmilga](https://github.com/NikaSmilga) on GitHub (Developer & Tester of SFC-enabled skills) 
-   Maria Molchanova, [mary-silence](https://github.com/mary-silence) on Github (PM, Dev Tools)
-   Maxim Talimanchuk, [mtalimanchuk](https://github.com/mtalimanchuk) on Github (DevOps)
-   Daniel Kornev, [DanielKornev](https://github.com/DanielKornev) on Github (CPO)

Special thanks to Yuri Kuratov, [yurakuratov](https://github.com/yurakuratov) on Github (Senior Researcher at DeepPavlov.ai)

## Original Draw.io Extension Contributors

-   Henning Dieterichs, [hediet](https://github.com/hediet) on Github (Main Contributor / Author)
-   Vincent Rouillé, [Speedy37](https://github.com/Speedy37) on Github

## See Also / Similar Extensions

-   [Draw.io](https://app.diagrams.net/) - This extension relies on the giant work of Draw.io. Their embedding feature enables this extension! This extension bundles a recent version of Draw.io.
-   [vscode-drawio](https://github.com/eightHundreds/vscode-drawio) by eightHundreds.

## Research Paper
-   [Discourse-Driven Integrated Dialogue Development Environment for Open-Domain Dialogue Systems](https://aclanthology.org/2021.codi-main.4/)

## Other Cool Conversational AI Tech by DeepPavlov

If you like this extension, you might like [our other Conversational AI tech](https://deeppavlov.ai) too:

-   **[DeepPavlov Library](https://www.github.com/deepmipt/deeppavlov)**: An open-source Conversational AI library (Python, TF 1.x, PyTorch).
-   **[DeepPavlov Dream](https://www.github.com/deepmipt/dream)**: An open-source Multiskill AI Assistant Platform.
-   **[DeepPavlov Agent](https://www.github.com/deepmipt/dp-agent)**: An open-source Conversational AI orchestrator (it used by DeepPavlov Dream).
