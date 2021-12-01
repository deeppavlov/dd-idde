const vscode = acquireVsCodeApi();

function saveAsPng(event) {
  const input_elements = document.querySelectorAll('.formbuilder-text [name]')
  const data = {}
  input_elements.forEach((node) => data[node.name] = node.value)
  console.log(data)
  data.old_titles = JSON.parse(data.old_titles)
  vscode.postMessage({
    command: 'saveAsPng', form_data: JSON.stringify(data)
  });
}


const saveAsPngButton = document.getElementById('saveAsPngButton');
saveAsPngButton.addEventListener('click', saveAsPng);

const exTitle = document.getElementById('example-title')
const sfcs = document.getElementById('sfc-selector');
const examples = document.getElementById('sfc-examples')
const updateEx = (ev) => {
  if (ev.target.value === '----') {
    examples.style.display = 'none'
    exTitle.style.display = 'none'
  } else {
    examples.style.display = 'block'
    exTitle.style.display = 'block'
  }
  if (ev.target.value in window.SFCExamples) {
    console.warn('found example!')
    examples.innerHTML = window.SFCExamples[ev.target.value].map(l => `<p>${l}</p>`).join('\n')
  } else {
    examples.innerHTML = "---"
  }
}
sfcs.addEventListener('change', updateEx)
updateEx({ target: sfcs })

Array.from(document.getElementsByClassName('connected_node_node')).forEach(element => {
  el_id = element.id;
  el_cell_id = element.cell_id;
  element.addEventListener('click', () => {
    vscode.postMessage({
      command: 'editCell',
      cell_id: el_id,
    })
  });
});

Array.from(document.getElementsByClassName('connected_node_sfc')).forEach(element => {
  var el_id = element.id;
  var el_cell_id = element.cell_id;
  element.addEventListener('click', () => {
    var el_select = document.getElementById(`option_${el_id}`);
    var selected_sfc = el_select.options[el_select.selectedIndex].text;
    var el_opt = document.getElementById(`cond ${el_id}`);
    var opt_text = el_opt.value;
    // tgt_cell = document.getElementsByClassName("connected_node_node").getElementById(el_id);
    // tg
    // vscode.postMessage({
    //   command: 'editEdge',
    //   cell_id: el_id,
    //   sfc: "aa"
    // })
    vscode.postMessage({
      command: 'editEdge',
      cell_id: el_id,
      sfc: selected_sfc,
      cond: opt_text
    })
  });
});


function addRow(tableID) {

  var table = document.getElementById(tableID);

  var rowCount = table.rows.length;
  var row = table.insertRow(rowCount);

  var colCount = table.rows[0].cells.length;

  for (var i = 0; i < colCount; i++) {

    var newcell = row.insertCell(i);

    newcell.innerHTML = table.rows[0].cells[i].innerHTML;
    //alert(newcell.childNodes);
    switch (newcell.childNodes[0].type) {
      case "text":
        newcell.childNodes[0].value = "";
        break;
      case "checkbox":
        newcell.childNodes[0].checked = false;
        break;
      case "select-one":
        newcell.childNodes[0].selectedIndex = 0;
        break;
    }
  }
}

function deleteRow(tableID) {
  try {
    var table = document.getElementById(tableID);
    var rowCount = table.rows.length;

    for (var i = 0; i < rowCount; i++) {
      var row = table.rows[i];
      var chkbox = row.cells[0].childNodes[0];
      if (null != chkbox && true == chkbox.checked) {
        if (rowCount <= 1) {
          alert("Cannot delete all the rows.");
          break;
        }
        table.deleteRow(i);
        rowCount--;
        i--;
      }


    }
  } catch (e) {
    alert(e);
  }
}
