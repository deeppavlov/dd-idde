import { EventEmitter } from "@hediet/std/events";
import { Disposable } from "@hediet/std/disposable";
import { DrawioConfig, DrawioEvent, DrawioAction } from "./DrawioTypes";
import { WebviewPanel, window, ViewColumn, ExtensionContext } from "vscode";
import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';

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

	constructor(
		private readonly messageStream: MessageStream,
		private readonly getConfig: () => Promise<DrawioConfig>,
		public readonly reloadWebview: () => void,
		private readonly vwPanel: WebviewPanel,
		private readonly context: ExtensionContext
	) {
		this.dispose.track(
			messageStream.registerMessageHandler((msg) => {
				console.log("1 " + msg as string);
				this.handleEvent(JSON.parse(msg as string) as DrawioEvent);
			}
			)
		);
		this.vwP = vwPanel;
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
			const oldXml = this.currentXml;
			this.currentXml = drawioEvt.xml;
			this.onChangeEmitter.emit({ newXml: this.currentXml, oldXml });
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
		} else if (drawioEvt.event === "oleg") {
			this.vwP.webview.postMessage({ oleg: "Privet" });
			let webviewPanel = window.createWebviewPanel(
				'vscodeTest',
				'VsCode test webview',
				ViewColumn.One,
				{
					enableScripts: true
				}
			);
			webviewPanel.webview.onDidReceiveMessage(
				message => {
					switch (message.command) {
						case 'saveAsPng':
							this.saveAsPng(message.text);
							return;
					}
				},
				undefined,
				this.context.subscriptions
			);
			this.setHtmlContent(webviewPanel.webview, this.context);
			let form_content = { "FirstName": "Oleg", "Age": 244 };
			// this.setHtmlContent(webviewPanel.webview, context);
			// WV = vscode.window.createWebView; WV.setHTMLContent(); 
			// .onDidReceiveMessage(
			// 	message => {
			// 	  switch (message.command) {
			// 		case 'saveAsPng':
			// 		  saveAsPng(message.text);
			// 		  return;
			// 	  }
			// 	},
			// 	undefined,
			// 	context.subscriptions
			//   );

			this.onInitEmitter.emit();
		} else {
			this.onUnknownMessageEmitter.emit({ message: drawioEvt });
		}
	}

	private setHtmlContent(webview: vscode.Webview, extensionContext: vscode.ExtensionContext) {
		let htmlContent = `<html>
		<head>
		  <meta charset="UTF-8">
		  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src cspSource; script-src 'nonce-nonce';">
		  <meta name="viewport" content="width=device-width, initial-scale=1.0">
		  <link href="vscodeTest.css" rel="stylesheet">
		</head>
		<body>
		  <div id="canvasSection"><canvas id="vscodeTestCanvas" /></div>
		  <form id="MyForm">
			<label for="fname">First name:</label><br>
			<input type="text" id="fname" name="fname" value="John"><br>
			<label for="lname">Last name:</label><br>
			<input type="text" id="lname" name="lname" value="Doe"><br><br>
			<input type="button" id="saveAsPngButton" value="Save as png">
		  </form> 
		  <script type="text/javascript" src="vscodeTest.js"></script>
		</body>
	  </html>`;
		const jsFilePath = vscode.Uri.joinPath(extensionContext.extensionUri, 'javascript', 'vscodeTest.js');
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

	public async mergeXmlLike(xmlLike: string): Promise<void> {
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

	/**
	 * This loads an xml or svg+xml Draw.io diagram.
	 */
	public loadXmlLike(xmlLike: string) {
		this.currentXml = undefined;
		this.sendAction({
			action: "load",
			xml: xmlLike,
			autosave: 1,
		});
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
		} else if (extension.endsWith(".svg")) {
			return await this.exportAsSvgWithEmbeddedXml();
		} else {
			throw new Error(
				`Invalid file extension "${extension}"! Only ".png", ".svg" and ".drawio" are supported.`
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
