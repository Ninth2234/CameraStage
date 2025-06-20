console.log("hello")

const mCanvas = document.getElementById("machine_frame");
const mCtx = mCanvas.getContext("2d");

const camWidth = 100;
const camHeight = 50;

let rect = {x:100,y:100,width:50,height:50};
let dragging = false;
let offsetX, offsetY;

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
});



