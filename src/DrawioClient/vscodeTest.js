
// const canvas = document.getElementById('vscodeTestCanvas');

function saveAsPng(event) {
  // Call back to the extension context to save the image to the workspace folder.
  const vscode = acquireVsCodeApi();
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

