window.initializeCameras = function (view) {
    var grid = view.querySelector(".camera-grid");
    if (!grid) {
        return function () {};
    }

    var detail = view.querySelector(".camera-detail");
    var detailName = view.querySelector("#camera-detail-name");
    var detailImage = view.querySelector(".camera-detail-image");
    var backButton = view.querySelector(".camera-back");
    var cards = view.querySelectorAll(".camera-card");
    var selectedCard = null;
    var refreshTimer;
    var active = true;

    function imageUrl(camera) {
        return "/api/cameras/" + camera + "/latest.jpg?t=" + new Date().getTime();
    }

    function refreshImage(image, camera) {
        image.src = imageUrl(camera);
    }

    function refreshGrid() {
        var index;
        if (selectedCard) {
            return;
        }
        for (index = 0; index < cards.length; index += 1) {
            refreshImage(cards[index].querySelector(".camera-image"), cards[index].getAttribute("data-camera"));
        }
    }

    function showGrid() {
        selectedCard = null;
        detail.hidden = true;
        grid.hidden = false;
        refreshGrid();
    }

    function showDetail(card) {
        selectedCard = card;
        detailName.textContent = card.getAttribute("data-camera-name");
        detailImage.alt = card.getAttribute("data-camera-name") + " camera snapshot";
        grid.hidden = true;
        detail.hidden = false;
        refreshImage(detailImage, card.getAttribute("data-camera"));
    }

    function bindImage(image, container) {
        image.onload = function () {
            if (active) {
                container.className = container.className.replace(" unavailable", "");
            }
        };
        image.onerror = function () {
            if (active && container.className.indexOf("unavailable") === -1) {
                container.className += " unavailable";
            }
        };
    }

    for (var index = 0; index < cards.length; index += 1) {
        (function (card) {
            bindImage(card.querySelector(".camera-image"), card);
            card.onclick = function () {
                showDetail(card);
            };
        }(cards[index]));
    }
    bindImage(detailImage, detail);
    backButton.onclick = showGrid;

    refreshGrid();
    refreshTimer = window.setInterval(function () {
        if (selectedCard) {
            refreshImage(detailImage, selectedCard.getAttribute("data-camera"));
        } else {
            refreshGrid();
        }
    }, 8000);

    return function () {
        active = false;
        window.clearInterval(refreshTimer);
    };
};
