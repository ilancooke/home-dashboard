window.initializeCameras = function (view) {
    var grid = view.querySelector(".camera-grid");
    if (!grid) {
        return function () {};
    }

    var detail = view.querySelector(".camera-detail");
    var detailName = view.querySelector("#camera-detail-name");
    var detailImage = view.querySelector(".camera-detail-image");
    var liveVideo = view.querySelector(".camera-live-video");
    var liveStatus = view.querySelector(".camera-live-status");
    var refreshStatus = view.querySelector("#camera-refresh-status");
    var backButton = view.querySelector(".camera-back");
    var cards = view.querySelectorAll(".camera-card");
    var selectedCard = null;
    var refreshTimer;
    var active = true;
    var liveAttempt = 0;
    var liveSocket = null;
    var liveObjectUrl = null;
    var liveTimeout = null;
    var liveConnected = false;

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

    function setLiveStatus(message) {
        liveStatus.textContent = message;
    }

    function setRefreshStatus(message) {
        refreshStatus.textContent = message;
    }

    function stopLive() {
        liveAttempt += 1;
        liveConnected = false;
        if (liveTimeout !== null) {
            window.clearTimeout(liveTimeout);
            liveTimeout = null;
        }
        if (liveSocket !== null) {
            liveSocket.close();
            liveSocket = null;
        }
        liveVideo.pause();
        liveVideo.removeAttribute("src");
        if (liveObjectUrl !== null) {
            (window.URL || window.webkitURL).revokeObjectURL(liveObjectUrl);
            liveObjectUrl = null;
        }
        liveVideo.hidden = true;
        setRefreshStatus("Snapshots refresh every 8 seconds");
    }

    function showSnapshotFallback(attempt) {
        if (!active || attempt !== liveAttempt || liveConnected) {
            return;
        }
        if (liveSocket !== null) {
            liveSocket.close();
            liveSocket = null;
        }
        liveVideo.hidden = true;
        setLiveStatus("Live video unavailable — showing snapshots");
        setRefreshStatus("Snapshots refresh every 8 seconds");
    }

    function appendVideoData(sourceBuffer, queue, data) {
        if (sourceBuffer.updating || queue.length) {
            queue.push(data);
            return;
        }
        try {
            sourceBuffer.appendBuffer(data);
        } catch (error) {
            queue.length = 0;
        }
    }

    function startMseStream(url, attempt) {
        var mediaSource = new MediaSource();
        var sourceBuffer = null;
        var queue = [];
        var objectUrl = (window.URL || window.webkitURL).createObjectURL(mediaSource);

        liveObjectUrl = objectUrl;
        liveVideo.src = objectUrl;
        mediaSource.addEventListener("sourceopen", function () {
            if (!active || attempt !== liveAttempt) {
                return;
            }
            try {
                liveSocket = new WebSocket(url);
                liveSocket.binaryType = "arraybuffer";
            } catch (error) {
                showSnapshotFallback(attempt);
                return;
            }
            liveSocket.onopen = function () {
                liveSocket.send(JSON.stringify({
                    type: "mse",
                    value: "avc1.640029,avc1.64002A,avc1.640033,hvc1.1.6.L153.B0,mp4a.40.2,mp4a.40.5,opus",
                }));
            };
            liveSocket.onmessage = function (event) {
                var message;
                if (!active || attempt !== liveAttempt) {
                    return;
                }
                if (typeof event.data === "string") {
                    try {
                        message = JSON.parse(event.data);
                        if (message.type !== "mse") {
                            return;
                        }
                        sourceBuffer = mediaSource.addSourceBuffer(message.value);
                        sourceBuffer.addEventListener("updateend", function () {
                            if (queue.length && !sourceBuffer.updating) {
                                appendVideoData(sourceBuffer, queue, queue.shift());
                            }
                        });
                        liveConnected = true;
                        liveVideo.hidden = false;
                        setLiveStatus("Live video");
                        setRefreshStatus("Live video is playing");
                        if (liveTimeout !== null) {
                            window.clearTimeout(liveTimeout);
                            liveTimeout = null;
                        }
                        var play = liveVideo.play();
                        if (play && play.catch) {
                            play.catch(function () {});
                        }
                    } catch (error) {
                        showSnapshotFallback(attempt);
                    }
                    return;
                }
                if (sourceBuffer !== null && event.data instanceof ArrayBuffer) {
                    appendVideoData(sourceBuffer, queue, event.data);
                }
            };
            liveSocket.onerror = function () {
                showSnapshotFallback(attempt);
            };
            liveSocket.onclose = function () {
                showSnapshotFallback(attempt);
            };
        });
    }

    function startLive(camera) {
        var attempt;
        var xhr;
        stopLive();
        attempt = liveAttempt;
        setLiveStatus("Connecting to live video…");
        if (!window.MediaSource || !window.WebSocket || !window.URL) {
            showSnapshotFallback(attempt);
            return;
        }
        xhr = new XMLHttpRequest();
        xhr.open("GET", "/api/cameras/" + camera + "/live", true);
        xhr.timeout = 10000;
        xhr.onreadystatechange = function () {
            var response;
            if (xhr.readyState !== 4 || !active || attempt !== liveAttempt) {
                return;
            }
            if (xhr.status < 200 || xhr.status >= 300) {
                showSnapshotFallback(attempt);
                return;
            }
            try {
                response = JSON.parse(xhr.responseText);
            } catch (error) {
                showSnapshotFallback(attempt);
                return;
            }
            startMseStream(response.url, attempt);
        };
        xhr.onerror = function () {
            showSnapshotFallback(attempt);
        };
        xhr.ontimeout = function () {
            showSnapshotFallback(attempt);
        };
        xhr.send();
        liveTimeout = window.setTimeout(function () {
            showSnapshotFallback(attempt);
        }, 10000);
    }

    function showGrid() {
        stopLive();
        selectedCard = null;
        detail.hidden = true;
        grid.hidden = false;
        setRefreshStatus("Snapshots refresh every 8 seconds");
        refreshGrid();
    }

    function showDetail(card) {
        stopLive();
        selectedCard = card;
        detailName.textContent = card.getAttribute("data-camera-name");
        detailImage.alt = card.getAttribute("data-camera-name") + " camera snapshot";
        grid.hidden = true;
        detail.hidden = false;
        setRefreshStatus("Starting live video…");
        refreshImage(detailImage, card.getAttribute("data-camera"));
        startLive(card.getAttribute("data-camera"));
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
            if (!liveConnected) {
                refreshImage(detailImage, selectedCard.getAttribute("data-camera"));
            }
        } else {
            refreshGrid();
        }
    }, 8000);

    return function () {
        active = false;
        window.clearInterval(refreshTimer);
        stopLive();
    };
};
