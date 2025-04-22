document.querySelector('#darkmode_toggle').addEventListener('click', function() {
  const isDark = document.documentElement.classList.toggle('dark');
  localStorage.setItem('theme', isDark ? 'dark' : 'light');
  if (document.documentElement.classList.contains('dark')) {
    resizeAndDraw(canvas);
  }
});

document.querySelector('#order_toggle').addEventListener('click', function() {
  const isDesc = document.getElementById('order_select').value === 'desc';
  document.getElementById('order_select').value = isDesc ? 'asc' : 'desc';
  let toggle = document.getElementById('order_toggle');
  toggle.classList.toggle('fa-arrow-up');
  toggle.classList.toggle('fa-arrow-down');

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
