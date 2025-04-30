/* global htmx */

document.querySelector('#darkmode_toggle').addEventListener('click', function() {
  const isDark = document.documentElement.classList.toggle('dark');
  localStorage.setItem('theme', isDark ? 'dark' : 'light');
  if (document.documentElement.classList.contains('dark')) {
    resizeAndDraw(canvas);
  }
});

document.querySelector('#order_toggle').addEventListener('click', function() {
  const isDesc = document.getElementById('order_select').value === 'desc';
  const order_select = document.getElementById("order_select");
  order_select.value = isDesc ? 'asc' : 'desc';
  const toggle = document.getElementById('order_toggle');
  toggle.classList.toggle('rotate-180');
  toggle.classList.toggle('fa-arrow-down');
  htmx.trigger(order_select, 'change');
});

document.querySelector('#filters_toggle').addEventListener('click', function() {
  let toggle = document.getElementById('filters');
  toggle.classList.toggle('hidden');
});

const canvas = document.getElementById('bg-canvas');

function resizeCanvas(canvas) {
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;
}

function drawStars(canvas) {
  /**
   * Draw stars on said canvas
   */
  let ctx = canvas.getContext("2d");
  let imgData = new ImageData(canvas.offsetWidth, canvas.offsetHeight);
  let arr = imgData.data;

  for (let i = 0; i < arr.length; i += 4) {
    let rand = Math.random();
    if (rand > 0.99) {
      let intensity = Math.floor(Math.random() * 255);
      // let r = Math.floor(Math.random() * 255);
      // let g = Math.floor(Math.random() * 255);
      // let b = Math.floor(Math.random() * 255);
      arr[i] = intensity;
      arr[i + 1] = intensity;
      arr[i + 2] = intensity;
      arr[i + 3] = 255;
    } else {
      arr[i] = 0;
      arr[i + 1] = 0;
      arr[i + 2] = 0;
      arr[i + 3] = 255;
    }
  }
  ctx.putImageData(imgData, 0, 0);
}

function resizeAndDraw(canvas) {
  resizeCanvas(canvas);
  drawStars(canvas);
}

if (document.documentElement.classList.contains('dark')) {
  // Initial draw
  resizeAndDraw(canvas);
}

// Redraw on resize
window.addEventListener('resize', () => resizeAndDraw(canvas));

// Filters dropdown close button logic
const filtersCloseBtn = document.getElementById('filters_close');
if (filtersCloseBtn) {
  filtersCloseBtn.addEventListener('click', function() {
    document.getElementById('filters').classList.add('hidden');
  });
}

/* Context Editor */
var context_editor = document.getElementById('context_editor');
if (context_editor){
  var quill = new Quill(`#${context_editor.id}`, {
    theme: "snow",
    modules: {
      toolbar: [
        [{ 'header': 1 }, { 'header': 2 }],
        ['bold', 'italic', 'underline'],
        ['blockquote', 'code-block'],
        ['link', 'image']
      ]
    },
    readOnly: true,
  });

  const context_edit = document.getElementById('context_edit');
  const context_cancel = document.getElementById('context_cancel');
  const context_save = document.getElementById('context_save');

  var ql_toolbar = document.querySelector('.ql-toolbar');
  ql_toolbar.classList.add('hidden');
  var ql_editor = document.querySelector('.ql-editor');

  var context_editor_form = document.getElementById('context_editor_form');
  var context_html_input = document.getElementById('context_html_input');

  context_edit.addEventListener('click', function() {
    quill.enable();
    ql_toolbar.classList.remove('hidden');
    context_cancel.classList.remove('hidden');
    context_save.classList.remove('hidden');
    context_edit.classList.add('hidden');
    context_cancel.classList.add('flex');
    context_save.classList.add('flex');
    ql_editor.style.resize = "vertical";
  });
  context_cancel.addEventListener('click', function() {
    quill.disable();
    ql_toolbar.classList.add('hidden');
    context_cancel.classList.add('hidden');
    context_save.classList.add('hidden');
    context_edit.classList.remove('hidden');
    context_cancel.classList.remove('flex');
    context_save.classList.remove('flex');
    ql_editor.style.resize = "none";
    
    let url = context_editor_form.getAttribute('hx-post');
    
    htmx.ajax('GET', url, "#context_editor_container");
  });
  context_save.addEventListener('click', function() {
    quill.disable();
    ql_toolbar.classList.add('hidden');
    context_cancel.classList.add('hidden');
    context_save.classList.add('hidden');
    context_edit.classList.remove('hidden');
    context_cancel.classList.remove('flex');
    context_save.classList.remove('flex');
    ql_editor.style.resize = "none";

    context_html_input.value = quill.root.innerHTML;
    htmx.trigger(context_editor_form, 'submit');
  });


  document.body.addEventListener('htmx:afterSwap', function(evt) {
    if (evt.target.id === 'context_editor_container'){
      context_editor = document.getElementById('context_editor');
      quill = new Quill(`#${context_editor.id}`, {
        theme: "snow",
        modules: {
          toolbar: [
            [{ 'header': 1 }, { 'header': 2 }],
            ['bold', 'italic', 'underline'],
            ['blockquote', 'code-block'],
            ['link', 'image']
          ]
        },
        readOnly: true,
      });

      ql_toolbar = document.querySelector('.ql-toolbar');
      ql_toolbar.classList.add('hidden');
      ql_editor = document.querySelector('.ql-editor');

      context_editor_form = document.getElementById('context_editor_form');
      context_html_input = document.getElementById('context_html_input');
    }
  });
}

// Lightning Tip Modal logic
(function() {
  const tipBtn = document.getElementById('tip_lightning_btn');
  const tipModal = document.getElementById('tip_lightning_modal');
  const tipClose = document.getElementById('tip_lightning_close');
  const invoiceEl = document.getElementById('lightning_invoice');
  const feedbackEl = document.getElementById('tip_feedback');

  if (tipBtn && tipModal && tipClose) {
    tipBtn.addEventListener('click', () => {
      tipModal.classList.remove('hidden');
      document.body.style.overflow = 'hidden';
    });
    tipClose.addEventListener('click', () => {
      tipModal.classList.add('hidden');
      document.body.style.overflow = '';
    });
    tipModal.addEventListener('click', (e) => {
      if (e.target === tipModal) {
        tipModal.classList.add('hidden');
        document.body.style.overflow = '';
      }
    });
    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape') {
        tipModal.classList.add('hidden');
        document.body.style.overflow = '';
      }
    });
  }
  if (invoiceEl && feedbackEl) {
    invoiceEl.addEventListener('click', () => {
      navigator.clipboard.writeText(invoiceEl.textContent).then(() => {
        feedbackEl.textContent = 'Invoice copied!';
        setTimeout(() => { feedbackEl.textContent = ''; }, 1200);
      });
    });
  }
})();
