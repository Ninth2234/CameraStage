console.log("hello")

const mCanvas = document.getElementById("machine_frame");
const mCtx = mCanvas.getContext("2d");

const camWidth = 200;
const camHeight = 200;

const px_to_mm = 0.3;

const machine_limits = {x:[50,120],y:[50,120]};


let rect = {x:100,y:100,width:50,height:50};
let dragging = false;
let offsetX, offsetY;

function convertPxToMachine(x_px,y_px){
    x_machine = x_px*px_to_mm+machine_limits.x[0];
    y_machine = y_px*px_to_mm+machine_limits.y[0];
    return [x_machine,y_machine]
}

function draw(){
    console.log("call draw")
    // mCtx.clearRect(0,0, mCanvas.width, mCanvas.height);
    mCtx.strokeStyle = "black";
    mCtx.strokeRect(0,0, 20, 500);
}

function drawRect(x,y,w,h){
    mCtx.clearRect(0, 0, mCanvas.width, mCanvas.height);
    mCtx.strokeStyle = "black";
    mCtx.strokeRect(x,y,w,h)
}


function clampToBounds(x, y) {
    return [
        Math.max(0, Math.min(x, mCanvas.width - camWidth)),
        Math.max(0, Math.min(y, mCanvas.height - camHeight))
    ];
}

mCanvas.addEventListener("mousedown", (e) => {
    const rectmCanvas = mCanvas.getBoundingClientRect();
    const xClick = e.clientX - rectmCanvas.left;
    const yClick = e.clientY - rectmCanvas.top;

    // Center rectangle on click
    let xCorner = xClick - Math.round(camWidth / 2);
    let yCorner = yClick - Math.round(camHeight / 2);

    // Clamp to mCanvas bounds
    const [xNew, yNew] = clampToBounds(xCorner, yCorner);

    console.log("Click at:", xClick, yClick);
    console.log("Clamped to:", xNew, yNew);

    drawRect(xNew, yNew, camWidth, camHeight);


    machineCoords = convertPxToMachine(xNew,yNew);
    machine_move(machineCoords[0],machineCoords[1])
});


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
