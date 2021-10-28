const alertsContainer = $('#alerts');

let uniqueIds = [];

function addAlert({message, category}) {
    let currentHTML = alertsContainer.html();
    let uniqueId = generateUniqueId();
    let htmlStr = `<div id="Message-${uniqueId}" class="alert alert-${category}">${message}</div>`;
    currentHTML += htmlStr;
    alertsContainer.html(currentHTML);
    setTimeout(() => deleteAlert(uniqueId), 3000);
}

function deleteAlert(msgId) {
    const msgToDelete = $(`#Message-${msgId}`); 
    msgToDelete.fadeOut(500, function(){
        msgToDelete.remove()
    })
    removeIdFromWatchList(msgId);
}

function generateUniqueId() {
    let tryId = "id" + Math.random().toString(16).slice(2);
    while (uniqueIds.includes(tryId)) {
        tryId = "id" + Math.random().toString(16).slice(2);
    }
    uniqueIds.push(tryId);
    return tryId
}

function removeIdFromWatchList(id) {
    let index = uniqueIds.indexOf(id);
    if (index !== -1) {
        uniqueIds.splice(index, 1);
    }
}

alertsContainer.ready(handleFlashAlerts);

function handleFlashAlerts() {
    let flashAlerts = alertsContainer.find('.flash');
    if (flashAlerts.length > 0) {
        setTimeout(() => {
            flashAlerts.fadeOut(500, function(){
                flashAlerts.remove()
            })
        }, 3000) 
    }
}
