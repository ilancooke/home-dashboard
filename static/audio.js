window.initializeAudio = function (view) {
    if (!view.querySelector(".zone-grid")) {
        return function () {};
    }
    var requests = [];
    var active = true;
    var zoneStates = {};
    var pageMessage = view.querySelector("#page-message");

    function request(method, url, body, callback) {
        var xhr = new XMLHttpRequest();
        requests.push(xhr);
        xhr.timeout = 10000;
        xhr.open(method, url, true);
        xhr.setRequestHeader("Accept", "application/json");
        if (body !== null) {
            xhr.setRequestHeader("Content-Type", "application/json");
        }
        xhr.onreadystatechange = function () {
            var response;
            if (xhr.readyState !== 4 || !active) {
                return;
            }
            requests.splice(requests.indexOf(xhr), 1);
            try {
                response = JSON.parse(xhr.responseText);
            } catch (error) {
                response = {error: "Invalid response from dashboard"};
            }
            if (xhr.status >= 200 && xhr.status < 300) {
                callback(null, response);
            } else {
                callback(response.error || "Audio request failed");
            }
        };
        xhr.send(body === null ? null : JSON.stringify(body));
    }

    function setBusy(card, busy) {
        var controls = card.querySelectorAll("button, select, input");
        var index;
        card.className = busy ? "zone-card updating" : "zone-card";
        for (index = 0; index < controls.length; index += 1) {
            controls[index].disabled = busy;
        }
    }

    function renderZone(status) {
        var card = view.querySelector("#zone-" + status.zone);
        if (card === null) {
            return;
        }
        var state = card.querySelector(".state");
        var power = card.querySelector(".power-button");
        var source = card.querySelector(".source-select");
        var mute = card.querySelector(".mute-button");
        var volume = card.querySelector(".volume-slider");

        zoneStates[status.zone] = status;
        state.textContent = status.power ? "On" : "Off";
        state.className = status.power ? "state on" : "state";
        power.textContent = status.power ? "Turn off" : "Turn on";
        power.className = status.power ? "power-button active" : "power-button";
        source.value = String(status.source);
        mute.textContent = status.mute ? "Unmute" : "Mute";
        mute.className = status.mute ? "mute-button active" : "mute-button";
        volume.value = status.volume;
        card.querySelector(".volume-value").textContent = status.volume;
        setBusy(card, false);
    }

    function showError(message) {
        pageMessage.textContent = message;
    }

    function loadZones() {
        request("GET", "/api/audio/zones", null, function (error, zones) {
            var index;
            if (error) {
                showError(error);
                return;
            }
            for (index = 0; index < zones.length; index += 1) {
                renderZone(zones[index]);
            }
            pageMessage.textContent = "";
        });
    }

    function updateZone(zone, control, body) {
        var card = view.querySelector("#zone-" + zone);
        setBusy(card, true);
        pageMessage.textContent = "";
        request(
            "POST",
            "/api/audio/zones/" + zone + "/" + control,
            body,
            function (error, status) {
                if (error) {
                    setBusy(card, false);
                    showError(error);
                    return;
                }
                renderZone(status);
            }
        );
    }

    function bindCard(card) {
        var zone = Number(card.getAttribute("data-zone"));
        var volume = card.querySelector(".volume-slider");

        card.querySelector(".power-button").onclick = function () {
            updateZone(zone, "power", {on: !zoneStates[zone].power});
        };
        card.querySelector(".source-select").onchange = function () {
            updateZone(zone, "source", {source: Number(this.value)});
        };
        card.querySelector(".mute-button").onclick = function () {
            updateZone(zone, "mute", {muted: !zoneStates[zone].mute});
        };
        volume.oninput = function () {
            card.querySelector(".volume-value").textContent = this.value;
        };
        volume.onchange = function () {
            updateZone(zone, "volume", {volume: Number(this.value)});
        };
    }

    var cards = view.querySelectorAll(".zone-card");
    var index;
    for (index = 0; index < cards.length; index += 1) {
        bindCard(cards[index]);
    }

    loadZones();
    var pollTimer = window.setInterval(loadZones, 30000);
    return function () {
        active = false;
        window.clearInterval(pollTimer);
        for (var index = 0; index < requests.length; index += 1) {
            requests[index].abort();
        }
    };
};
