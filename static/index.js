
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
        body: JSON.stringify({ msg: "G28\nG1X80Y80Z90" })
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

document.getElementById("clear_img").addEventListener('click',()=>{
    fetch("/clear", {
            method: "POST"
        });
})

document.getElementById("download_img").addEventListener('click',()=>{
    const link = document.createElement('a');
    link.href = '/stitch?format=png&scale=1.0';  // adjust format/scale if needed
    link.download = 'stitched_output.png';       // this triggers a download
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
})

document.getElementById("download_fusion_img").addEventListener('click', () => {
    const link = document.createElement('a');
    link.href = '/stitch/fusion360?overlay=true';  // or any other query
    link.download = '';  // triggers browser download instead of navigation
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
});


const imageObj = new Image();

// 📦 Draw rectangle around camera view
function drawCameraRect(x, y, width, height, layer) {
    console.log("REDRAW")
    const rect = new Konva.Rect({
            x: x,
            y: y,
            width: width,
            height: height,
            stroke: 'red',
            strokeWidth: 2,
            dash: [4, 4],
            name: 'camera-view'
        });

    // Optional: Remove previous rectangle
    previous = layer.find('.camera-view');
    previous.forEach(obj => obj.destroy());  // Destroy each shape
    layer.add(rect);
    layer.draw();
}

function updateBackgroundImage() {
    imageObj.onload = () => {
        const bgImage = new Konva.Image({
            x: 0,
            y: 0,
            image: imageObj,
            width: canvasWidth,
            height: canvasHeight,
        });
        backgroundLayer.add(bgImage);
        backgroundLayer.draw();
        console.log("hello")
    };
    imageObj.src = "/stitch?format=jpg&scale=0.1"; // or MJPEG frame, etc.
    console.log("hello2")
}



const backgroundLayer = new Konva.Layer();
const overlayLayer = new Konva.Layer();
const drawLayer = new Konva.Layer();

async function init(){
    const response = await fetch("/config");
    config = await response.json();

    machine_limits = config.machine_limits;

    px_to_mm = config.canvas_size_mm[0]/500; // priortize height over width
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



    stage.add(backgroundLayer);
    stage.add(overlayLayer);
    stage.add(drawLayer);

    updateBackgroundImage();
    


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
        
        drawCameraRect(camera_rect_corner[0],camera_rect_corner[1],camWidth,camHeight,drawLayer)

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

    const respPos = await fetch('http://192.168.31.254:5005/pos');
    machinePos = await respPos.json();

    x = (machinePos.x-machine_limits.x[0])*mm_to_px;
    y = canvasHeight-(machinePos.y-machine_limits.y[0])*mm_to_px-camHeight;
    console.log(x,y)
    camera_rect_corner = [x,y];
    drawCameraRect(camera_rect_corner[0],camera_rect_corner[1],camWidth,camHeight,drawLayer);
    // Start the update loop
    update();
}
init();

function request_stitch() {
    fetch("/stitch?new=true",{
        method:"POST"
    })
}

 
document.getElementById("stitch").addEventListener('click',()=>{
    request_stitch();
})

document.getElementById("scan").addEventListener('click',()=>{
    fetch("/scan");
})

document.getElementById("reset_connection").addEventListener('click',()=>{
    fetch("http://localhost:5005/reconnect",{
        method:"POST"
    });
})



socket.on("newStitchAvailable", () => {
    console.log("NEW STITCH AVAILABLE")
    updateBackgroundImage();
});

socket.on("scanFinish", () => {
    console.log("SCAN FINSIH")
    request_stitch();
});

socket.on("captureFinish", () => {
    request_stitch();
});