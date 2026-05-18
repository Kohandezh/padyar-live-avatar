let currentIndex = 0;
let activeVideo = 1;
const video1 = document.getElementById("video1");
const video2 = document.getElementById("video2");

function playNextVideo(video_src) {
    
    const currentVideo = activeVideo === 1 ? video1 : video2;
    const nextVideo = activeVideo === 1 ? video2 : video1;

    nextVideo.src = video_src;
    currentVideo.pause();
    nextVideo.load();

    nextVideo.oncanplay = () => {
        nextVideo.play().then(() => {
            nextVideo.style.opacity = "1";
            setTimeout(() => {
                currentVideo.style.opacity = "0";
                currentVideo.pause();
            }, 50);
        }).catch(error => console.error("Autoplay failed:", error));
    };

    activeVideo = activeVideo === 1 ? 2 : 1;
}

function changeVideo(option) {
    playNextVideo(`videos/${option}.mp4`);
    
  }

const input_text = document.getElementById('menu1');

// Expand the input width when clicked
input_text.addEventListener('click', function(event) {
input_text.style.width = '50%'; // New width when clicked
event.stopPropagation(); // Prevent the body click event from triggering
});

// Shrink the input width when clicking anywhere on the body
document.body.addEventListener('click', function() {
input_text.style.width = '30%'; // Original width
});

// const response = NaN
let data = null;  // Define global variable
let array = [];

async function sendRequest() {
    const inputText = document.getElementById('inputText').value;
    // const responseContainer = document.getElementById('responseContainer');

    // Clear previous response
    // responseContainer.innerHTML = 'Processing...';
    try {
        const response = await fetch("https://c243-34-124-142-0.ngrok-free.app/process", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({input: inputText}),
            mode: 'cors',  // Ensures CORS headers are sent
        })
        data = await response.json();  // Parse JSON response

        await get_generated_video()
        // console.log(data);  // Output the received array
        
        // const videoBlob = await response.blob();  // ✅ Convert response to blob
        // const videoUrl = URL.createObjectURL(videoBlob);  // ✅ Create a URL for the video

        // const audioElement = document.getElementById("videoPlayer");
        // audioElement.src = videoUrl;
        // audioElement.play();  // ✅ Play the video
    } catch (error) {
        console.log(error.message)
        // responseContainer.innerHTML = 'Error: ' + error.message;
    }
}

async function get_generated_video() {
    // const responseContainer = document.getElementById('responseContainer');

    // Clear previous response
    // responseContainer.innerHTML = 'Processing...';
    console.log(data.length)
    for (let item=0; item<data.length; item++){
        console.log(item)
        try {
            const response = await fetch("https://c243-34-124-142-0.ngrok-free.app/generate", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({chunk: data[item]}),
                mode: 'cors',  // Ensures CORS headers are sent
            })
            // data = await response.json();  // Parse JSON response
            // console.log(data);  // Output the received array
            
            const videoBlob = await response.blob();  // ✅ Convert response to blob
            const videoUrl = URL.createObjectURL(videoBlob);  // ✅ Create a URL for the video
            array.push(videoUrl);

            // if (item == 1){show_video()}
            show_video()

            // const audioElement = document.getElementById("videoPlayer");
            // audioElement.src = videoUrl;
            // audioElement.play();  // ✅ Play the video
        } catch (error) {
            console.log(error.message)
            // responseContainer.innerHTML = 'Error: ' + error.message;
        }
    }
}

async function show_video() {

    function playNextVideo() {
    
        const currentVideo = activeVideo === 1 ? video1 : video2;
        const nextVideo = activeVideo === 1 ? video2 : video1;
        console.log("length of array:", array.length)

        if (currentIndex >= array.length) return;

        nextVideo.src = array[currentIndex++];
        nextVideo.load();

        nextVideo.oncanplay = () => {
            nextVideo.play().then(() => {
                nextVideo.style.opacity = "1";
                setTimeout(() => {
                    currentVideo.style.opacity = "0";
                    currentVideo.pause();
                }, 500);
            }).catch(error => console.error("Autoplay failed:", error));
        };

        activeVideo = activeVideo === 1 ? 2 : 1;
    }

    // Start first video
    video1.src = array[currentIndex++];
    video1.play().catch(error => console.error("Autoplay failed:", error));
    video1.style.opacity = "1";

    video1.addEventListener("ended", playNextVideo);
    video2.addEventListener("ended", playNextVideo);
    document.getElementById('container').addEventListener("click", () => {
        video1.muted = false;
        video2.muted = false;
    }, { once: true });
            
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}
