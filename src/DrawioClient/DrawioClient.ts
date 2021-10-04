import { EventEmitter } from "@hediet/std/events";
import { Disposable } from "@hediet/std/disposable";
import { DrawioConfig, DrawioEvent, DrawioAction } from "./DrawioTypes";
import { WebviewPanel, window, ViewColumn, ExtensionContext, Uri } from "vscode";
import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';
import { title } from "process";
import { node } from "webpack";
import { VsCodeSetting } from "../vscode-utils/VsCodeSetting";
import * as FormData from 'form-data';
import { request } from "http";
import { PythonShell } from 'python-shell';

/**
 * Represents a connection to an drawio iframe.
 */
export class DrawioClient<
	TCustomAction extends {} = never,
	TCustomEvent extends {} = never
	> {
	public readonly dispose = Disposable.fn();

	private readonly onInitEmitter = new EventEmitter();
	public readonly onInit = this.onInitEmitter.asEvent();

	protected readonly onChangeEmitter = new EventEmitter<
		DrawioDocumentChange
	>();
	public readonly onChange = this.onChangeEmitter.asEvent();

	private readonly onSaveEmitter = new EventEmitter();
	public readonly onSave = this.onSaveEmitter.asEvent();

	private readonly onUnknownMessageEmitter = new EventEmitter<{
		message: TCustomEvent;
	}>();
	public readonly onUnknownMessage = this.onUnknownMessageEmitter.asEvent();

	// This is always up to date, except directly after calling load.
	private currentXml: string | undefined = undefined;

	private vwP: WebviewPanel;
	private openedForms: { [key: string]: WebviewPanel };
	private openedDFFs: { [key: string]: WebviewPanel };
	private visibility: boolean = false;
	private ts: number = 0;

	constructor(
		private readonly messageStream: MessageStream,
		private readonly getConfig: () => Promise<DrawioConfig>,
		public readonly reloadWebview: () => void,
		private readonly vwPanel: WebviewPanel,
		private readonly context: ExtensionContext,
		private readonly sfc_url: VsCodeSetting<string>
	) {
		this.openedForms = {};
		this.openedDFFs = {};
		this.dispose.track(
			messageStream.registerMessageHandler((msg) => {
				this.handleEvent(JSON.parse(msg as string) as DrawioEvent);
			}
			)
		);
		this.vwP = vwPanel;
		(window as any).suggestions_visible = false;



	}

	private currentActionId = 0;
	private responseHandlers = new Map<
		string,
		{ resolve: (response: DrawioEvent) => void; reject: () => void }
	>();

	protected sendCustomAction(action: TCustomAction): void {
		this.sendAction(action);
	}

	protected sendCustomActionExpectResponse(
		action: TCustomAction
	): Promise<TCustomEvent> {
		return this.sendActionWaitForResponse(action);
	}

	private sendAction(action: DrawioAction | TCustomAction) {
		this.messageStream.sendMessage(JSON.stringify(action));
	}

	private sendActionWaitForResponse(
		action: DrawioAction
	): Promise<DrawioEvent>;
	private sendActionWaitForResponse(
		action: TCustomAction
	): Promise<TCustomEvent>;
	private sendActionWaitForResponse(
		action: DrawioAction | TCustomAction
	): Promise<DrawioEvent | TCustomEvent> {
		return new Promise((resolve, reject) => {
			const actionId = (this.currentActionId++).toString();

			this.responseHandlers.set(actionId, {
				resolve: (response) => {
					this.responseHandlers.delete(actionId);
					resolve(response);
				},
				reject,
			});

			this.messageStream.sendMessage(
				JSON.stringify(Object.assign(action, { actionId }))
			);
		});
	}

	protected async handleEvent(evt: { event: string }): Promise<void> {
		const drawioEvt = evt as DrawioEvent;
		window.showInformationMessage(evt.event);
		if ("message" in drawioEvt) {
			const actionId = (drawioEvt.message as any).actionId as
				| string
				| undefined;
			if (actionId) {
				const responseHandler = this.responseHandlers.get(actionId);
				this.responseHandlers.delete(actionId);
				if (responseHandler) {
					responseHandler.resolve(drawioEvt);
				}
			}
		} else if (drawioEvt.event === "init") {
			this.onInitEmitter.emit();
		} else if (drawioEvt.event === "autosave") {
			// Prevent lags while exchanging data between WebView and Extension
			if (this.vwPanel.active) {
				const oldXml = this.currentXml;
				this.currentXml = drawioEvt.xml;
				this.onChangeEmitter.emit({ newXml: this.currentXml, oldXml });
			};
		} else if (drawioEvt.event === "save") {
			const oldXml = this.currentXml;
			this.currentXml = drawioEvt.xml;
			if (oldXml != this.currentXml) {
				// a little bit hacky.
				// If "save" does trigger a change,
				// treat save as autosave and don't actually save the file.
				this.onChangeEmitter.emit({ newXml: this.currentXml, oldXml });
			} else {
				// Otherwise, the change has already
				// been reported by autosave.
				this.onSaveEmitter.emit();
			}
		} else if (drawioEvt.event === "export") {
			// sometimes, message is not included :(
			// this is a hack to find the request to resolve
			const vals = [...this.responseHandlers.values()];
			this.responseHandlers.clear();
			if (vals.length !== 1) {
				for (const val of vals) {
					val.reject();
				}
			} else {
				vals[0].resolve(drawioEvt);
			}
		} else if (drawioEvt.event === "configure") {
			const config = await this.getConfig();
			this.sendAction({
				action: "configure",
				config,
			});
		} else if (drawioEvt.event === "open dff") {
			// begin oleg
			/*
			var curfil = (this as any)._doc.document.uri.path;
			const readStream = fs.createReadStream(curfil);
			const form = new FormData();
			form.append('drawio', readStream);
			let text = "";
			const req = request(
				{
					host: 'localhost',
					port: '5000',
					path: '/drawio2dff',
					method: 'POST',
					headers: form.getHeaders(),
				},
				response => {
					const chunks: Uint8Array[] = [];
					response.on('data', (chunk) => {
						chunks.push(chunk);
					});
					response.on('end', () => {
						const result = Buffer.concat(chunks).toString();
						var res_parsed = JSON.parse(result);
						var dff_base64 = res_parsed.dff;
						let buff = Buffer.from(dff_base64, 'base64');
						text += buff.toString('utf-8');
						var parsed = path.parse(curfil);
						var resfil = path.join(parsed.dir, parsed.name + "_dff.py")
						// if (!fs.existsSync(resfil)) {
						fs.writeFile(resfil, text, () => { });
						// }
						// vscode.window.showInformationMessage("hey! " + f);

						if (!this.openedDFFs.hasOwnProperty(resfil)) {
							let col_to_open = ViewColumn.Two;

							vscode.workspace.openTextDocument(resfil).then(doc => {
								vscode.window.showTextDocument(doc, col_to_open);
							});

							// webviewPanel.onDidDispose(
							// 	() => { delete this.openedDFFs[f] }, null, this.context.subscriptions
							// )
						}
						else {
							let vwP = this.openedDFFs[resfil];
							vwP.reveal()
						}
					});
				}
			);

			form.pipe(req);
			// end oleg
			*/
			


			/* Edited Request (Stable version of request to Flask server) */
			
			var content = (this as any)._doc.document.getText();
			var curfil = (this as any)._doc.document.uri.path;
			// window.showInformationMessage(`Current file content: ${content}`);

			const data = JSON.stringify({
				drawio: content
			})
			let text = "";

			const options = {
				host: 'localhost',
				port: '5000',
				path: '/drawio2dff',
				method: 'POST',
				headers: {
				  'Content-Type': 'application/json',
				}
			  }
			const req = request(options, res => {
				const chunks: Uint8Array[] = [];
				res.on('data', (chunk) => {
					chunks.push(chunk);
				});
				res.on('end', () => {
					const result = Buffer.concat(chunks).toString();
					var res_parsed = JSON.parse(result);
					var dff_base64 = res_parsed.dff;
					let buff = Buffer.from(dff_base64, 'base64');
					text += buff.toString('utf-8');
					var parsed = path.parse(curfil);
					var resfil = path.join(parsed.dir, parsed.name + "_dff.py")
					var resfilUri = Uri.file(resfil);
					fs.writeFile(resfilUri.fsPath, text, () => {
						if (!this.openedDFFs.hasOwnProperty(resfil)) {
							let col_to_open = ViewColumn.Two;

							vscode.workspace.openTextDocument(resfil).then(doc => {
								vscode.window.showTextDocument(doc, col_to_open);
							});
						}
						else {
							let vwP = this.openedDFFs[resfil];
							vwP.reveal()
						}
					});
				})
			});
			  
			req.on('error', error => {
				// POST failed, send message to WebView
				this.vwP.webview.postMessage({ connectionError: "showDFFConnError"});
				console.log(error);
			})
			
			req.write(data)
			req.end()
			/* End of edited request */

		} else if (drawioEvt.event === "get_suggs") {
			const speech_functions = ['Open.Attend',
				'Open.Demand.Fact',
				'Open.Demand.Opinion',
				'Open.Give.Fact',
				'Open.Give.Opinion',
				'React.Rejoinder.Confront.Challenge.Counter',
				'React.Rejoinder.Confront.Response.Re-challenge',
				'React.Rejoinder.Support.Challenge.Rebound',
				'React.Rejoinder.Support.Response.Resolve',
				'React.Rejoinder.Support.Track.Check',
				'React.Rejoinder.Support.Track.Clarify',
				'React.Rejoinder.Support.Track.Confirm',
				'React.Rejoinder.Support.Track.Probe',
				'React.Respond.Confront.Disengage',
				'React.Respond.Confront.Reply.Contradict',
				'React.Respond.Confront.Reply.Disagree',
				'React.Respond.Confront.Reply.Disawow',
				'React.Respond.Support.Develop.Elaborate',
				'React.Respond.Support.Develop.Enhance',
				'React.Respond.Support.Develop.Extend',
				'React.Respond.Support.Engage',
				'React.Respond.Support.Register',
				'React.Respond.Support.Reply.Acknowledge',
				'React.Respond.Support.Reply.Affirm',
				'React.Respond.Support.Reply.Agree',
				'React.Respond.Support.Response.Resolve',
				'Sustain.Continue.Monitor',
				'Sustain.Continue.Prolong.Elaborate',
				'Sustain.Continue.Prolong.Enhance',
				'Sustain.Continue.Prolong.Extend'];
			var cells_i: any[] = []
			let ts = Date.now();
			let delta = ts - this.ts;
			if (delta > 1000) {
				this.ts = ts;
				var vis = this.visibility;
				const fs = require('fs');
				var rp = require('request-promise');
				var sfcs: Array<string> = []
				speech_functions.forEach((sf) => {
					sfcs.push(sf);
				});
				drawioEvt.cells.forEach((cel) => {
					var cel_sfc = cel.sfc;
					sfcs.push(cel_sfc);
				});
				var options = {
					method: 'POST',
					uri: this.sfc_url.get(),
					body: sfcs,
					json: true // Automatically stringifies the body to JSON
				};
				var basic_sfcs: any = {};
				rp(options)
					.then((parsedBody: any) => {
						var predictions = parsedBody[0].batch;
						vscode.window.showInformationMessage(JSON.stringify(predictions));
						// POST succeeded...
						for (var j = 0; j < speech_functions.length; j++) {

							var curr_preds: any = [];
							predictions[j].forEach((pred: any) => {
								if (Object.keys(pred).length > 0) {
									curr_preds.push({ sug: pred.prediction, conf: pred.confidence });
								}
							});
							basic_sfcs[speech_functions[j]] = curr_preds;
						}
						// for is in cells:
						for (var is in drawioEvt.cells) {
							var i = Number(is);
							var cel = drawioEvt.cells[i];
							var cel_preds = predictions[i + speech_functions.length]
							var sug_sf: any[] = []
							cel_preds.forEach((pred_: any) => {
								if (Object.keys(pred_).length > 0) {
									sug_sf.push({ sug: pred_.prediction, conf: pred_.confidence });
								}
							});
							if (!(cel.x == 0 && cel.y == 0 && cel.h == 0 && cel.w == 0)) {
								cells_i.push({
									x: cel.x, y: cel.y, h: cel.h, w: cel.w,
									sty: cel.sty, sug_sf: sug_sf,
									id: cel.id
								})
							}

						}

						this.vwP.webview.postMessage({
							oleg: "DrawSuggestions",
							cells: cells_i
							, visibility: !vis,
							nodes_suggestions: basic_sfcs

						});
					})
					.catch((err: any) => {
						// POST failed, send message to WebView
						this.vwP.webview.postMessage({ connectionError: "getSuggsError", statusCode: err.statusCode});
						console.log(err);
					});

				this.visibility = !vis;

			}


		} else if (drawioEvt.event === "oleg") {
			let cid = drawioEvt.cell_id;
			let cell_title = drawioEvt.cell_title;
			let cell_content = JSON.parse(drawioEvt.curr_content);
			let node_info = {
				"cell_id": cid,
				"title": cell_title,
				"cell_content": cell_content,
				"children": drawioEvt.children,
				"suggs": drawioEvt.suggs
			}
			if (!this.openedForms.hasOwnProperty(cid)) {
				// vscode.window.showInformationMessage(cid);


				let col_to_open = ViewColumn.Two;

				let webviewPanel = window.createWebviewPanel(
					'vscodeTest',
					cell_title,
					(col_to_open as ViewColumn),
					{
						enableScripts: true,
						retainContextWhenHidden: true
					}
				);
				(webviewPanel as any)._cid = cid;
				this.openedForms[cid] = webviewPanel;
				(webviewPanel as any)._drawiovw = this.vwP.webview;
				webviewPanel.webview.onDidReceiveMessage(
					message => {
						switch (message.command) {
							case 'saveAsPng':
								var form_data = message.form_data;
								vscode.window.showInformationMessage(form_data);

								// this.saveAsPng(message.text);
								webviewPanel.dispose();
								(webviewPanel as any)._drawiovw.postMessage({ oleg: "Privet", cell_id: cid, data: form_data });
								break;
							// vscode.window.showInformationMessage("closed a panel");
							// return;
							case 'editCell':
								var cell_id = message.cell_id;

								webviewPanel.dispose();
								(webviewPanel as any)._drawiovw.postMessage({ oleg: "editCell", cell_id: cell_id });
								break;
							case 'editEdge':
								var cell_id = message.cell_id;

								var sfc = message.sfc;
								var cond = message.cond;
								// vscode.window.showInformationMessage(JSON.stringify({ sfc: sfc, cid: cell_id }));
								webviewPanel.dispose();

								// (webviewPanel as any)._drawiovw.postMessage({ oleg: "editEdge", cell_id: cell_id, sfc: sfc });
								(webviewPanel as any)._drawiovw.postMessage({ oleg: "editEdge", cell_id: cell_id, sfc: sfc, cond: cond });

						}
					},
					undefined,
					this.context.subscriptions
				);
				webviewPanel.onDidDispose(
					() => { delete this.openedForms[(webviewPanel as any)._cid] }, null, this.context.subscriptions
				)
				this.setHtmlContent(webviewPanel.webview, this.context, node_info);
			}
			else {
				let vwP = this.openedForms[cid];
				vwP.reveal()
			}

			this.onInitEmitter.emit();
		} else {
			this.onUnknownMessageEmitter.emit({ message: drawioEvt });
		}
	}

	private setHtmlContent(webview: vscode.Webview,
		extensionContext: vscode.ExtensionContext,
		node_info: any) {

		const base_speech_functions = ['Open.Attend',
			'Open.Demand.Fact',
			'Open.Demand.Opinion',
			'Open.Give.Fact',
			'Open.Give.Opinion',
			'React.Rejoinder.Confront.Challenge.Counter',
			'React.Rejoinder.Confront.Response.Re-challenge',
			'React.Rejoinder.Support.Challenge.Rebound',
			'React.Rejoinder.Support.Response.Resolve',
			'React.Rejoinder.Support.Track.Check',
			'React.Rejoinder.Support.Track.Clarify',
			'React.Rejoinder.Support.Track.Confirm',
			'React.Rejoinder.Support.Track.Probe',
			'React.Respond.Confront.Disengage',
			'React.Respond.Confront.Reply.Contradict',
			'React.Respond.Confront.Reply.Disagree',
			'React.Respond.Confront.Reply.Disawow',
			'React.Respond.Support.Develop.Elaborate',
			'React.Respond.Support.Develop.Enhance',
			'React.Respond.Support.Develop.Extend',
			'React.Respond.Support.Engage',
			'React.Respond.Support.Register',
			'React.Respond.Support.Reply.Acknowledge',
			'React.Respond.Support.Reply.Affirm',
			'React.Respond.Support.Reply.Agree',
			'React.Respond.Support.Response.Resolve',
			'Sustain.Continue.Monitor',
			'Sustain.Continue.Prolong.Elaborate',
			'Sustain.Continue.Prolong.Enhance',
			'Sustain.Continue.Prolong.Extend'];
		var speech_functions: any = [];
		if (node_info["suggs"]) {
			var suggs = JSON.parse(node_info["suggs"]);
			suggs.forEach((sug: any) => {
				var s = sug["sug"];
				var c = Number(sug["conf"]).toFixed(2);
				speech_functions.push(`${s} ${c}`);
			});
		}
		if (speech_functions.length == 0) {
			speech_functions = base_speech_functions
		}
		var title = node_info["title"].split(' ')[0];
		var node_info_sfc = node_info["cell_content"]["sfc"]
		if (!node_info_sfc) { node_info_sfc = '' }
		let htmlContent2 = `
		<head>
		  <meta charset="UTF-8">
		  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src cspSource; script-src 'nonce-nonce';">
		  <meta name="viewport" content="width=device-width, initial-scale=1.0">
		  <link href="vscodeTest.css" rel="stylesheet">
		</head>
		<div class="rendered-form">
		<div class="formbuilder-text form-group field-text-1627806340486">
		    <form id="MyForm">
			<label for="text-1627806340486" class="formbuilder-text-label">Title</label>
			<input type="text" placeholder="Node Title" class="form-control" 
			       name="node_title" access="false" value="${title}" 
				   id="b">
			<br/>
			<p>SFC</p><select name="sfc">`
		speech_functions.forEach((element: any) => {
			htmlContent2 += `<option value="${element}"`
			if (node_info_sfc === element) {
				htmlContent2 += ` selected`
			}
			htmlContent2 += `>${element}</option>`
		});
		htmlContent2 += `</select>
			</form>
		</div>
		<input type="button" id="saveAsPngButton" value="Save">
		`

		var children_li = "<ul>"
		node_info["children"].forEach((children: any) => {
			var children_title = children["title"];
			var children_cond = children["condition"];
			if (!children_cond) {
				children_cond = '';
			}
			var cond_splitted = children_cond.split(' ');
			var cond_ = cond_splitted[0];
			var proba = cond_splitted[1];
			if (!cond_) { cond_ = ''; }
			if (!proba) { proba = ''; }
			proba = proba.replace(' ', '').replace('(p=', '').replace(')', '');
			var children_cell_id = children["cell_id"];
			var children_sfc = children["sfc"];
			var children_el = `<li>		` +
				`<input type="button" class="connected_node_node" id="${children_cell_id}" value="${children_title}">` +
				`<select name="children_sfc" id="option_${children_cell_id}">`;
			speech_functions.forEach((element: any) => {
				children_el += `<option value="${element}"`
				if (cond_ === element) {
					children_el += ` selected`
				}
				children_el += `>${element}</option>`
			});
			children_el +=
				`</select>` +
				`<input type="text" placeholder="condition" value="${proba}" id="cond ${children_cell_id}">` +
				`<input type="button" class="connected_node_sfc" id="${children_cell_id}" value="save">` +
				`</li>`
			children_li = children_li + children_el;
		});
		children_li = children_li + "</ul>"
		if (node_info["children"].length > 0) {
			htmlContent2 += `
			<div class="">
				<h4 access="false" id="control-3900261">Connected To<br></h4></div>
			</div>
			`
			htmlContent2 = htmlContent2 + `<div>${children_li}</div>`
		}
		let htmlContent = htmlContent2;
		htmlContent = htmlContent + `<script type="text/javascript" src="vscodeTest.js"></script>`;
		const jsFilePath = vscode.Uri.joinPath(extensionContext.extensionUri, 'src', 'DrawioClient', 'vscodeTest.js');
		const visUri = webview.asWebviewUri(jsFilePath);
		htmlContent = htmlContent.replace('vscodeTest.js', visUri.toString());

		const cssPath = vscode.Uri.joinPath(extensionContext.extensionUri, 'stylesheet', 'vscodeTest.css');
		const cssUri = webview.asWebviewUri(cssPath);
		htmlContent = htmlContent.replace('vscodeTest.css', cssUri.toString());

		const nonce = this.getNonce();
		htmlContent = htmlContent.replace('nonce-nonce', `nonce-${nonce}`);
		htmlContent = htmlContent.replace(/<script /g, `<script nonce="${nonce}" `);
		htmlContent = htmlContent.replace('cspSource', webview.cspSource);

		webview.html = htmlContent;
	}

	private getWorkspaceFolder(): string {
		var folder = vscode.workspace.workspaceFolders;
		var directoryPath: string = '';
		if (folder != null) {
			directoryPath = folder[0].uri.fsPath;
		}
		return directoryPath;
	}

	private writeFile(filename: string, content: string | Uint8Array, callback: () => void) {
		fs.writeFile(filename, content, function (err) {
			if (err) {
				return console.error(err);
			}
			callback();
		});
	}

	private saveAsPng(messageText: string) {
		const dataUrl = messageText;
		if (dataUrl.length > 0) {

			const workspaceDirectory = this.getWorkspaceFolder();
			const newFilePath = path.join(workspaceDirectory, 'VsCodeExtensionTest.json');
			this.writeFile(newFilePath, dataUrl, () => {
				vscode.window.showInformationMessage(`The file ${newFilePath} has been created in the root of the workspace.`);
			});
		}
	}

	private getNonce() {
		let text = '';
		const possible = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
		for (let i = 0; i < 32; i++) {
			text += possible.charAt(Math.floor(Math.random() * possible.length));
		}
		return text;
	}

	/**
	 * Convert Python code to XML content
	 */
	 public async convertPyData(): Promise<any> {
		return new Promise((resolve, reject) => {
			let pyData = (this as any)._doc.document.getText();
			let xmlData = "";
			if (!pyData) {
				return;
			}
			const pathToPyScript = vscode.Uri.file(
				path.join(this.context.extensionPath, 'python-shell-scripts/py2drawio.py')
			);
			let shell = new PythonShell(pathToPyScript.fsPath, { mode: 'text' });
			shell.send(pyData);

			shell.on('message', function (batch) {
				// received a message sent from the Python script
				xmlData += batch;
				});
				
			// end the input stream and allow the process to exit
			shell.end( (err,code,signal) => {
				if (err) throw err;
				resolve(xmlData);
			});
		})
	};

	/**
	 * Convert Drawio XML to Python code
	 */
	public async convertDrawio2Py(newXML: string): Promise<any> {
		return new Promise((resolve, reject) => {
			// let pyData = (this as any)._doc.document.getText();
			let jsonData = {
				xmlData: newXML,
				pyData: (this as any)._doc.document.getText()
			}
			let chunks = "";
			const pathToPyScript = vscode.Uri.file(
				path.join(this.context.extensionPath, 'python-shell-scripts/drawio2py.py')
			);
			let shell = new PythonShell(pathToPyScript.fsPath, { mode: 'text' });
			shell.send(JSON.stringify(jsonData));

			shell.on('message', function (batch) {
				// received a message sent from the Python script
				chunks += batch
				});
				
			// end the input stream and allow the process to exit
			shell.end( (err, code, signal) => {
				if (err) throw err;
				console.log('The exit code was: ' + code);
				console.log('The exit signal was: ' + signal);
				console.log('finished');
				const result = chunks;
				var res_parsed = JSON.parse(result);
				var dff_base64 = res_parsed.pyCode;
				let buff = Buffer.from(dff_base64, 'base64');
				let newPyCode = buff.toString('utf-8');
				resolve(newPyCode);
			});
		})
	};

	/**
	 * This changes an xml Draw.io diagram
	 * Modified for Python Scripts
	 */
	 public async mergeXmlLike(xmlLike: string): Promise<void> {
		//
		let currFile = (this as any)._doc.document.uri.path;
		if (currFile.endsWith(".py")) {
			this.convertPyData()
				.then(result => {
					const evt = this.sendActionWaitForResponse({
						action: "merge",
						xml: result,
					});
					this.vwP.webview.postMessage( { graphOperations: "rearrangeGraph" });
				})
				.catch(error => {
					console.log(error);
				});
		} else {
			const evt = await this.sendActionWaitForResponse({
				action: "merge",
				xml: xmlLike,
			});
			if (evt.event !== "merge") {
				throw new Error("Invalid response");
			}
			if (evt.error) {
				throw new Error(evt.error);
			}
		}
	}

	/**
	 * This loads an xml or svg+xml Draw.io diagram.
	 * Modified for Python Scripts
	 */
	public loadXmlLike(xmlLike: string) {
		let currFile = (this as any)._doc.document.uri.path;
		if (currFile.endsWith(".py")) {
			this.convertPyData()
				.then(result => {
					this.currentXml = undefined;
					this.sendAction({
						action: "load",
						xml: result,
						autosave: 1,
					});
					this.vwP.webview.postMessage( { graphOperations: "rearrangeGraph" });
				})
				.catch(error => {
					console.log(error);
				});
		} else {
			this.currentXml = undefined;
			this.sendAction({
				action: "load",
				xml: xmlLike,
				autosave: 1,
			});
		}
	}

	public async loadPngWithEmbeddedXml(png: Uint8Array): Promise<void> {
		let str = Buffer.from(png).toString("base64");
		this.loadXmlLike("data:image/png;base64," + str);
	}

	public async export(extension: string): Promise<Buffer> {
		if (extension.endsWith(".png")) {
			return await this.exportAsPngWithEmbeddedXml();
		} else if (
			extension.endsWith(".drawio") ||
			extension.endsWith(".dio")
		) {
			const xml = await this.getXml();
			return Buffer.from(xml, "utf-8");
		} else if (
			extension.endsWith(".dff")
		) {
			const dff = await this.getDff();
			return Buffer.from(dff, "utf-8");
		} else if (extension.endsWith(".svg")) {
			return await this.exportAsSvgWithEmbeddedXml();
		} else {
			throw new Error(
				`Invalid file extension "${extension}"! Only ".png", ".svg", ".drawio" and ".dff" are supported.`
			);
		}
	}

	protected async getXmlUncached(): Promise<string> {
		const response = await this.sendActionWaitForResponse({
			action: "export",
			format: "xml",
		});
		if (response.event !== "export") {
			throw new Error("Unexpected response");
		}
		return response.xml;
	}

	public async getXml(): Promise<string> {
		if (!this.currentXml) {
			const xml = await this.getXmlUncached();
			if (!this.currentXml) {
				// It might have been changed in the meantime.
				// Always trust autosave.
				this.currentXml = xml;
			}
		}
		return this.currentXml;
	}

	public async getDff(): Promise<string> {
		// var parser = new DOMParser();
		// var doc = parser.parseFromString(xml_str, "application/xml");
		let xml = await this.getXml();
		const jsdom = require("jsdom");
		const dom = new jsdom.JSDOM(xml);
		var defl = dom.window.document.querySelector("diagram").textContent; // 'Hello world'

		var data = Buffer.from(defl, "base64").toString("binary");
		console.log(data.length);

		// npm install pako
		var pako = require('pako');

		var inf = pako.inflateRaw(
			Uint8Array.from(data, c => c.charCodeAt(0)), { to: 'string' })
		var str = decodeURIComponent(inf);

		// zlib.unzip(inputBuffer, (err: any, buffer: any) => {
		// 	if (!err) {
		// 		defl = buffer.toString();
		// 	}
		// });



		return "oleg" + str;
	}

	public async exportAsPngWithEmbeddedXml(): Promise<Buffer> {
		const response = await this.sendActionWaitForResponse({
			action: "export",
			format: "xmlpng",
		});
		if (response.event !== "export") {
			throw new Error("Unexpected response");
		}
		const start = "data:image/png;base64,";
		if (!response.data.startsWith(start)) {
			throw new Error("Invalid data");
		}
		const base64Data = response.data.substr(start.length);
		return Buffer.from(base64Data, "base64");
	}

	public async exportAsSvgWithEmbeddedXml(): Promise<Buffer> {
		const response = await this.sendActionWaitForResponse({
			action: "export",
			format: "xmlsvg",
		});
		if (response.event !== "export") {
			throw new Error("Unexpected response");
		}
		const start = "data:image/svg+xml;base64,";
		if (!response.data.startsWith(start)) {
			throw new Error("Invalid data");
		}
		const base64Data = response.data.substr(start.length);
		return Buffer.from(base64Data, "base64");
	}

	public async exportAsDff(): Promise<Buffer> {
		const response = await this.sendActionWaitForResponse({
			action: "export",
			format: "xmlsvg",
		});
		if (response.event !== "export") {
			throw new Error("Unexpected response");
		}
		const start = "data:image/svg+xml;base64,";
		if (!response.data.startsWith(start)) {
			throw new Error("Invalid data");
		}
		const base64Data = response.data.substr(start.length);
		return Buffer.from(base64Data, "base64");
	}

	public triggerOnSave(): void {
		this.onSaveEmitter.emit();
	}
}

export interface DrawioDocumentChange {
	oldXml: string | undefined;
	newXml: string;
}

export interface MessageStream {
	registerMessageHandler(handler: (message: unknown) => void): Disposable;
	sendMessage(message: unknown): void;
}
