
const socket = io();
// const socket = io('http://localhost:5007'); // change to your server URL & port

// const mCanvas = document.getElementById("machine_frame");
// const mCtx = mCanvas.getContext("2d");

camWidth = 100;
camHeight = 80;

px_to_mm = 0.3;

machine_limits = {x:[50,120],y:[50,120]};

let camera_rect_corner = [0,0]
let stitchedImage = null;  // Global variable to store the stitched image

// async function setupCanvas(){
//     const response = await fetch("/config");
//     config = await response.json();

//     machine_limits = config.machine_limits;

//     const canvas = document.getElementById("machine_frame");
//     // canvas.width = config.canvas_size[0];
//     // canvas.height = config.canvas_size[1];

//     px_to_mm = config.canvas_size_mm[1]/canvas.height; // priortize height over width
//     mm_to_px = 1/px_to_mm;
//     canvas.width = config.canvas_size_mm[0]*mm_to_px;
//     canvas.height = config.canvas_size_mm[1]*mm_to_px;

//     camWidth = config.camera_size_mm[0]*mm_to_px;
//     camHeight = config.camera_size_mm[1]*mm_to_px;    
// }

// setupCanvas()





function convertPxToMachine(x_px,y_px){
    x_machine = x_px*px_to_mm+machine_limits.x[0];
    y_machine = machine_limits.y[1]-y_px*px_to_mm;
    return [x_machine,y_machine]
}

// function draw(){
//     console.log("call draw")
//     // mCtx.clearRect(0,0, mCanvas.width, mCanvas.height);
//     mCtx.strokeStyle = "black";
//     mCtx.strokeRect(0,0, 20, 500);
// // }

// function drawRect(x,y,w,h){
//     mCtx.strokeStyle = "black";
//     mCtx.strokeRect(x,y,w,h)
// }
// function reDraw(){
//     const canvas = document.getElementById("machine_frame");
//     const ctx = canvas.getContext("2d");
    
//     img = stitchedImage;
//     // Compute scale to fit image inside canvas
//     const scale = Math.min(
//         canvas.width / img.width,
//         canvas.height / img.height
//     );

//     const scaledWidth = img.width * scale;
//     const scaledHeight = img.height * scale;

//     const xOffset = (canvas.width - scaledWidth) / 2;
//     const yOffset = (canvas.height - scaledHeight) / 2;

//     ctx.clearRect(0, 0, canvas.width, canvas.height);
//     ctx.drawImage(img, xOffset, yOffset, scaledWidth, scaledHeight);

//     drawRect(camera_rect_corner[0], camera_rect_corner[1], camWidth, camHeight);
// }

// function clampToBounds(x, y) {
//     return [
//         Math.max(0, Math.min(x, mCanvas.width - camWidth)),
//         Math.max(0, Math.min(y, mCanvas.height - camHeight))
//     ];
// }

// mCanvas.addEventListener("mousedown", (e) => {
//     const rectmCanvas = mCanvas.getBoundingClientRect();
//     const xClick = e.clientX - rectmCanvas.left;
//     const yClick = e.clientY - rectmCanvas.top;

//     // Center rectangle on click
//     let xCorner = xClick - Math.round(camWidth / 2);
//     let yCorner = yClick - Math.round(camHeight / 2);

//     // Clamp to mCanvas bounds
//     const [xNew, yNew] = clampToBounds(xCorner, yCorner);

//     console.log("Click at:", xClick, yClick);
//     console.log("Clamped to:", xNew, yNew);

    
//     drawRect(xNew, yNew, camWidth, camHeight);

//     camera_rect_corner = [xNew,yNew];

//     machineCoords = convertPxToMachine(xNew,yNew);
//     machine_move(machineCoords[0],machineCoords[1])
// });


function machine_move(x, y) {
    fetch("http://192.168.31.254:5005/gcode", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ msg: `G90\nG1 X${x} Y${y}` })
    })
    .then(res => res.json())
    .then(data => console.log("Machine moved:", data))
    .catch(err => console.error("Move error:", err));
}



document.getElementById("home").addEventListener("click", async () => {

    fetch("http://192.168.31.254:5005/gcode", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ msg: "G28\nG1Z120\nG1X80Y80" })
    })

});


document.getElementById("move_up").addEventListener("click", async () => {
    fetch("http://192.168.31.254:5005/gcode", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ msg: "G91\nG1Z1\nG90" })
    })

});

document.getElementById("move_down").addEventListener("click", async () => {
    fetch("http://192.168.31.254:5005/gcode", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ msg: "G91\nG1Z-1\nG90" })
    })

});

async function setupSlider(){
    
    const res = await fetch("http://192.168.31.254:5006/exposure");
    const data = await res.json();
        
    if (data.status === "ok") {
      const slider = document.getElementById("exposure_range");

      // Set min, max, and current value
      slider.min = data.min;
      slider.max = data.max;
      slider.value = data.current;

      document.getElementById("exposure_value").value = data.current;
    }
}
setupSlider();
let debounceTimeout = null;
document.getElementById("exposure_range").addEventListener("input", e => {
    const value = e.target.value;
    document.getElementById("exposure_value").value = value;

    clearTimeout(debounceTimeout);
    debounceTimeout = setTimeout(() => {
        fetch("http://192.168.31.254:5006/exposure", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ value: value })
        });
    }, 200); // send only after 200 ms of inactivity
});


document.getElementById('capture').addEventListener('click',()=>{
    socket.emit('capture_request');
})

async function refreshStitch() {
    try {
        const response = await fetch("/stitch?scale=0.1&format=jpg", { cache: "no-cache" }); // prevent caching
        if (!response.ok) {
            throw new Error("Failed to fetch stitched image");
        }

    } catch (err) {
        console.error("Error loading stitched image:", err);
    }
}
document.getElementById("clear_img").addEventListener('click',()=>{
    fetch("/clear", {
            method: "POST"
        });
    refreshStitch();
})

document.getElementById("download_img").addEventListener('click',()=>{
    const link = document.createElement('a');
    link.href = '/stitch?format=png&scale=1.0';  // adjust format/scale if needed
    link.download = 'stitched_output.png';       // this triggers a download
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
})

document.getElementById("stitch_refresh").addEventListener('click',()=>{
    refreshStitch();
})

let imageObj = new Image();

async function init(){
    const response = await fetch("/config");
    config = await response.json();

    machine_limits = config.machine_limits;

    px_to_mm = config.canvas_size_mm[1]/500; // priortize height over width
    mm_to_px = 1/px_to_mm;
    canvasWidth = config.canvas_size_mm[0]*mm_to_px;
    canvasHeight = config.canvas_size_mm[1]*mm_to_px;

    camWidth = config.camera_size_mm[0]*mm_to_px;
    camHeight = config.camera_size_mm[1]*mm_to_px;    

    const stage = new Konva.Stage({
        container: 'Konva',
        width: canvasWidth,
        height: canvasHeight,
    });

    const backgroundLayer = new Konva.Layer();
    const overlayLayer = new Konva.Layer();
    const drawLayer = new Konva.Layer();

    stage.add(backgroundLayer);
    stage.add(overlayLayer);
    stage.add(drawLayer);

    // Example: add image placeholder (for stitched image)
    
    imageObj.onload = () => {
    const bgImage = new Konva.Image({
        x: 0,
        y: 0,
        image: imageObj,
        width: stage.width(),
        height: stage.height(),
    });
    backgroundLayer.add(bgImage);
    backgroundLayer.draw();
    };
    imageObj.src = "/stitch?use_cache=true"; // or MJPEG frame, etc.


    stage.on('click', (e) => {
        const pointerPos = stage.getPointerPosition();

        const rectWidth = camWidth;
        const rectHeight = camHeight;

        x = pointerPos.x-camWidth/2;
        y = pointerPos.y-camHeight/2;
        
        xNew = Math.max(0, Math.min(x, stage.width()-camWidth));
        yNew = Math.max(0, Math.min(y, stage.height()-camHeight));

        
        // let [xNew, yNew] = clampToBounds(x*px_to_mm,y*px_to_mm);
        camera_rect_corner = [xNew,yNew];
        
        const rect = new Konva.Rect({
            x: camera_rect_corner[0],
            y: camera_rect_corner[1],
            width: rectWidth,
            height: rectHeight,
            stroke: 'red',
            strokeWidth: 2,
            dash: [4, 4],
            name: 'camera-view'
        });

        // Optional: Remove previous rectangle
        previous = drawLayer.find('.camera-view');
        previous.forEach(obj => obj.destroy());  // Destroy each shape
        drawLayer.add(rect);
        drawLayer.draw();

        machineCoords = convertPxToMachine(xNew,yNew);
        machine_move(machineCoords[0],machineCoords[1])
    });

    const _liveImage = new Image();
    _liveImage.src = "http://192.168.31.254:5006/video";

    const liveImage = new Konva.Image({
        x: camera_rect_corner[0],
        y: camera_rect_corner[1],
        width:  camWidth,
        height: camHeight,
        image: _liveImage
    })

    drawLayer.add(liveImage)
    function update() {
        liveImage.image(_liveImage);
        liveImage.x(camera_rect_corner[0]);
        liveImage.y(camera_rect_corner[1]);
        drawLayer.batchDraw();
        requestAnimationFrame(update);
    }

    // Start the update loop
    update();
}
init();

function reloadStitch() {
    imageObj.src = "/stitch?cache_bust=" + new Date().getTime();
    console.log("hll")
}

document.getElementById("stitch_refresh").addEventListener('click',()=>{
    console.log("hi")
    reloadStitch();
})

document.getElementById("scan").addEventListener('click',()=>{
    fetch("/scan");
})
// const stage = new Konva.Stage({
//   container: 'Konva',
//   width: 500,
//   height: 500,
// });
// const backgroundLayer = new Konva.Layer();
// const overlayLayer = new Konva.Layer();

// stage.add(backgroundLayer);
// stage.add(overlayLayer);

// // Optional: draw grid or bounding box
// const grid = new Konva.Line({
//   points: [
//     0, 0,
//     stage.width(), 0,
//     stage.width(), stage.height(),
//     0, stage.height(),
//     0, 0
//   ],
//   stroke: '#aaa',
//   strokeWidth: 1,
// });


// overlayLayer.add(grid);

// // Example: add image placeholder (for stitched image)
// const imageObj = new Image();
// imageObj.onload = () => {
//   const bgImage = new Konva.Image({
//     x: 0,
//     y: 0,
//     image: imageObj,
//     width: stage.width(),
//     height: stage.height(),
//   });
//   backgroundLayer.add(bgImage);
//   backgroundLayer.draw();
// };
// imageObj.src = "/stitch"; // or MJPEG frame, etc.

// const drawLayer = new Konva.Layer();
// stage.add(drawLayer);

// stage.on('click', (e) => {
//   const pointerPos = stage.getPointerPosition();

//   const rectWidth = 100;
//   const rectHeight = 100;

//   const rect = new Konva.Rect({
//     x: pointerPos.x - rectWidth / 2,
//     y: pointerPos.y - rectHeight / 2,
//     width: rectWidth,
//     height: rectHeight,
//     stroke: 'red',
//     strokeWidth: 2,
//     dash: [4, 4],
//     name: 'camera-view'
//   });

//   // Optional: Remove previous rectangle
//   previous = drawLayer.find('.camera-view');
//   previous.forEach(obj => obj.destroy());  // Destroy each shape
//   drawLayer.add(rect);
//   drawLayer.draw();
// });
