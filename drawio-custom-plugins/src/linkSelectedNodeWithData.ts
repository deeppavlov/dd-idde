import {
	ConservativeFlattenedEntryParser,
	FlattenToDictionary,
	JSONValue,
} from "@hediet/json-to-dictionary";
import { sendEvent } from "./vscode";
import {
	window as vscode_window
} from "vscode";

Draw.loadPlugin((ui) => {
	sendEvent({ event: "pluginLoaded", pluginId: "linkSelectedNodeWithData" });

	let nodeSelectionEnabled = false;
	const graph = ui.editor.graph;
	const highlight = new mxCellHighlight(graph, "#00ff00", 8);

	const model = graph.model;
	let activeCell: DrawioCell | undefined = undefined;

	let events = [mxEvent.ADD, mxEvent.ADD_CELLS, mxEvent.ADD_OVERLAY, mxEvent.AFTER_PAINT,
	mxEvent.ALIGN_CELLS, mxEvent.BEFORE_PAINT, mxEvent.BEFORE_UNDO,
	mxEvent.BEGIN_UPDATE, mxEvent.CELL_CONNECTED, mxEvent.CELLS_ADDED,
	mxEvent.CELLS_FOLDED, mxEvent.CELLS_MOVED, mxEvent.CELLS_ORDERED,
	mxEvent.CELLS_REMOVED, mxEvent.CELLS_RESIZED, mxEvent.CELLS_TOGGLED,
	mxEvent.CHANGE, mxEvent.CLEAR, mxEvent.CONNECT, mxEvent.CONNECT_CELL,
	mxEvent.CONTINUE, mxEvent.DONE, mxEvent.DOWN, mxEvent.END_UPDATE,
	mxEvent.EXECUTE, mxEvent.FIRED, mxEvent.FLIP_EDGE, mxEvent.FOLD_CELLS,
	mxEvent.GROUP_CELLS, mxEvent.INSERT, mxEvent.LABEL_CHANGED,
	mxEvent.LAYOUT_CELLS, mxEvent.MARK, mxEvent.MOVE_CELLS, mxEvent.NOTIFY,
	mxEvent.ORDER_CELLS, mxEvent.PAINT, mxEvent.REDO, mxEvent.REMOVE_CELLS,
	mxEvent.REMOVE_CELLS_FROM_PARENT, mxEvent.REMOVE_OVERLAY, mxEvent.REPAINT,
	mxEvent.RESIZE_CELLS, mxEvent.ROOT, mxEvent.SCALE,
	mxEvent.SCALE_AND_TRANSLATE, mxEvent.SELECT, mxEvent.SPLIT_EDGE,
	mxEvent.START, mxEvent.START_EDITING, mxEvent.STOP, mxEvent.TOGGLE_CELLS,
	mxEvent.TRANSLATE, mxEvent.UNDO, mxEvent.UNGROUP_CELLS, mxEvent.UP, mxEvent.UPDATE_CELL_SIZE];

	for (const oleg of events) {

		graph.addListener(oleg, function (sender: any, evt: any) {
			vscode_window.showInformationMessage("pipa");
		})

	}

	graph.addListener(mxEvent.DOUBLE_CLICK, function (sender: any, evt: any) {
		vscode_window.showInformationMessage("Double Click")
		if (!nodeSelectionEnabled) {
			return;
		}

		var cell: any | null = evt.getProperty("cell");
		if (cell != null) {
			const data = getLinkedData(cell);
			const label = getLabelTextOfCell(cell);

			if (!data && !label.match(/#([a-zA-Z0-9_]+)/)) {
				return;
			}

			sendEvent({ event: "nodeSelected", label, linkedData: data });
			evt.consume();
		}
	});

	function getLabelTextOfCell(cell: any): string {
		const labelHtml = graph.getLabel(cell);
		const el = document.createElement("html");
		el.innerHTML = labelHtml; // label can be html
		return el.innerText;
	}

	const selectionModel = graph.getSelectionModel();
	selectionModel.addListener(mxEvent.CHANGE, (sender: any, evt: any) => {
		// selection has changed
		const cells = selectionModel.cells;
		if (cells.length >= 1) {
			const selectedCell = cells[0];
			activeCell = selectedCell;
			(window as any).hediet_Cell = selectedCell;
		} else {
			activeCell = undefined;
		}
	});

	const prefix = "hedietLinkedDataV1";
	const flattener = new FlattenToDictionary({
		parser: new ConservativeFlattenedEntryParser({
			prefix,
			separator: "_",
		}),
	});

	function getLinkedData(cell: { value: unknown }) {
		if (!mxUtils.isNode(cell.value)) {
			return undefined;
		}
		const kvs = [...(cell.value.attributes as any)]
			.filter((a) => a.name.startsWith(prefix))
			.map((a) => [a.name, a.value]);
		if (kvs.length === 0) {
			return undefined;
		}

		const r: Record<string, string> = {};
		for (const [k, v] of kvs) {
			r[k] = v;
		}
		return flattener.unflatten(r);
	}

	function setLinkedData(cell: any, linkedData: JSONValue) {
		let newNode: HTMLElement;
		if (!mxUtils.isNode(cell.value)) {
			const doc = mxUtils.createXmlDocument();
			const obj = doc.createElement("object");
			obj.setAttribute("label", cell.value || "");
			newNode = obj;
		} else {
			newNode = cell.value.cloneNode(true);
		}

		for (const a of [
			...((newNode.attributes as any) as { name: string }[]),
		]) {
			if (a.name.startsWith(prefix)) {
				newNode.attributes.removeNamedItem(a.name);
			}
		}

		const kvp = flattener.flatten(linkedData);
		for (const [k, v] of Object.entries(kvp)) {
			newNode.setAttribute(k, v);
		}

		// don't use cell.setValue as it does not trigger a change
		model.setValue(cell, newNode);
	}

	window.addEventListener("message", (evt) => {
		if (evt.source !== window.opener) {
			return;
		}

		console.log(evt);
		const data = JSON.parse(evt.data) as CustomDrawioAction;

		switch (data.action) {
			case "setNodeSelectionEnabled": {
				nodeSelectionEnabled = data.enabled;
				break;
			}
			case "linkSelectedNodeWithData": {
				if (activeCell !== undefined) {
					log("Set linkedData to " + data.linkedData);
					graph.model.beginUpdate();
					try {
						setLinkedData(activeCell, data.linkedData);
					} finally {
						graph.model.endUpdate();
					}
					highlight.highlight(graph.view.getState(activeCell));
					setTimeout(() => {
						highlight.highlight(null);
					}, 500);
				}
				break;
			}
			case "getVertices": {
				const vertices = Object.values(graph.model.cells)
					.filter((c) => graph.model.isVertex(c))
					.map((c: any) => ({ id: c.id, label: graph.getLabel(c) }));
				sendEvent({
					event: "getVertices",
					message: data,
					vertices: vertices,
				});
				break;
			}
			case "updateVertices": {
				const vertices = data.verticesToUpdate;

				graph.model.beginUpdate();
				try {
					for (const v of vertices) {
						const c = graph.model.cells[v.id];
						if (!c) {
							log(`Unknown cell "${v.id}"!`);
							continue;
						}
						if (graph.getLabel(c) !== v.label) {
							graph.model.setValue(c, v.label);
						}
					}
				} finally {
					graph.model.endUpdate();
				}
				break;
			}
			case "addVertices": {
				// why is this called twice?
				log("add vertices is being called");
				const vertices = data.vertices;

				graph.model.beginUpdate();
				try {
					let i = 0;
					for (const v of vertices) {
						graph.insertVertex(
							undefined,
							null,
							v.label,
							i * 120,
							0,
							100,
							50,
							"rectangle"
						);
						i++;
					}
				} finally {
					graph.model.endUpdate();
				}
				break;
			}
			default: {
				return;
			}
		}

		evt.preventDefault();
		evt.stopPropagation();
	});
});
