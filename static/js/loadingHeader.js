const allContent = $('#all-content');
const loadingContainer = $('#loading-container');

function randomRGB() {
    const r = Math.floor(Math.random() * 256);
    const b = Math.floor(Math.random() * 256);
    return `rgb(${r},0,${b})`
}

const letters = document.querySelectorAll('.letter');

setInterval(function() {
    for (let letter of letters) {
        letter.style.color = randomRGB();
    }
}, 750)

function startLoadScreen() {
    allContent.hide();
    loadingContainer.css("display", "block");
}

function endLoadScreen() {
    // window.location.reload(true);
    loadingContainer.css("display", "none");
    allContent.show()
}
