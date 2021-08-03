
// const canvas = document.getElementById('vscodeTestCanvas');

const vscode = acquireVsCodeApi();

function saveAsPng(event) {
  // Call back to the extension context to save the image to the workspace folder.
  const formElement = document.getElementById("MyForm");
  // document.body.innerHTML = "";
  const data = new FormData(formElement);
  const js = JSON.stringify(Object.fromEntries(data));
  vscode.postMessage({
    command: 'saveAsPng', form_data: js
  });
}


const saveAsPngButton = document.getElementById('saveAsPngButton');
saveAsPngButton.addEventListener('click', saveAsPng);

// const b2 = document.getElementById('connected_node');
// b2.addEventListener('click', saveAsPng);


// // const links = document.getElementsByClassName("connected_node");
// // const li = links[0];
Array.from(document.getElementsByClassName('connected_node')).forEach(element => {
  // element.addEventListener('click', a);
  el_id = element.id;
  // el_text = element.text;
  el_cell_id = element.cell_id;
  // condition_el = document.getElementById(`cond ${el_id}`);
  // condition = condition_el.value;
  element.addEventListener('click', () => {
    vscode.postMessage({
      command: 'editCell',
      cell_id: el_id,
      // cond_value: condition
    })
  });
});
// // const connode = document.getElementById('connected_node');
// // connode.addEventListener('click', a);


// // li.onclick = a

