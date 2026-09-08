(function () {
    var root = document.documentElement;
    var fullscreenButton = document.getElementById("fullscreen-button");
    var view = document.getElementById("dashboard-view");
    var styles = document.getElementById("view-styles");
    var message = document.getElementById("navigation-message");
    var links = document.querySelectorAll(".dashboard-nav a");
    var pendingRequest = null;
    var currentPath = window.location.pathname;
    var cleanupView = window.initializeAudio(view);

    function fullscreenElement() {
        return document.fullscreenElement || document.webkitFullscreenElement ||
            document.mozFullScreenElement || document.msFullscreenElement;
    }

    function updateFullscreenButton() {
        var active = !!fullscreenElement();
        fullscreenButton.textContent = active ? "Exit fullscreen" : "Fullscreen";
        fullscreenButton.setAttribute("aria-pressed", String(active));
    }

    fullscreenButton.onclick = function () {
        var active = fullscreenElement();
        var target = active ? document : root;
        var action = active ?
            (document.exitFullscreen || document.webkitExitFullscreen ||
                document.mozCancelFullScreen || document.msExitFullscreen) :
            (root.requestFullscreen || root.webkitRequestFullscreen ||
                root.mozRequestFullScreen || root.msRequestFullscreen);
        if (!action) {
            return;
        }
        try {
            var result = action.call(target);
            if (result && result.catch) {
                result.catch(function () {});
            }
        } catch (error) {
            // Some tablet browsers do not support fullscreen requests.
        }
    };
    ["fullscreenchange", "webkitfullscreenchange", "mozfullscreenchange", "MSFullscreenChange"].forEach(function (event) {
        document.addEventListener(event, updateFullscreenButton);
    });
    updateFullscreenButton();

    // Ordinary links remain usable when same-document navigation is unavailable.
    if (!window.DOMParser || !window.history.pushState) {
        return;
    }

    function showMessage(text) {
        message.textContent = text;
        message.hidden = !text;
    }

    function loadView(path, addHistory, refresh) {
        if (pendingRequest) {
            pendingRequest.abort();
        }
        var xhr = new XMLHttpRequest();
        pendingRequest = xhr;
        view.setAttribute("aria-busy", "true");
        showMessage(refresh ? "" : "Loading…");
        xhr.open("GET", path, true);
        xhr.timeout = 45000;
        xhr.setRequestHeader("Accept", "text/html");

        function fail() {
            if (pendingRequest !== xhr) {
                return;
            }
            pendingRequest = null;
            view.removeAttribute("aria-busy");
            showMessage(refresh ? "Weather could not refresh. Will retry automatically." :
                "Could not open this view. Tap its button to try again.");
            // A failed Back/Forward request must not leave the URL on another view.
            if (!addHistory && !refresh) {
                window.history.replaceState(null, "", currentPath);
            }
        }

        xhr.onload = function () {
            if (pendingRequest !== xhr) {
                return;
            }
            if (xhr.status < 200 || xhr.status >= 300) {
                fail();
                return;
            }
            var page = new DOMParser().parseFromString(xhr.responseText, "text/html");
            var nextView = page.getElementById("dashboard-view");
            var nextStyles = page.getElementById("view-styles");
            if (!nextView || !nextStyles) {
                fail();
                return;
            }
            cleanupView();
            styles.textContent = nextStyles.textContent;
            view.innerHTML = nextView.innerHTML;
            view.setAttribute("data-view", nextView.getAttribute("data-view"));
            document.title = page.title;
            currentPath = path;
            if (addHistory) {
                window.history.pushState(null, "", path);
            }
            for (var index = 0; index < links.length; index += 1) {
                if (links[index].getAttribute("href") === path) {
                    links[index].setAttribute("aria-current", "page");
                } else {
                    links[index].removeAttribute("aria-current");
                }
            }
            cleanupView = window.initializeAudio(view);
            pendingRequest = null;
            view.removeAttribute("aria-busy");
            showMessage("");
            if (!refresh) {
                view.focus();
                window.scrollTo(0, 0);
            }
        };
        xhr.onerror = fail;
        xhr.ontimeout = fail;
        xhr.send();
    }

    for (var index = 0; index < links.length; index += 1) {
        links[index].onclick = function (event) {
            if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || event.button > 0) {
                return;
            }
            event.preventDefault();
            var path = this.getAttribute("href");
            if (path === currentPath) {
                if (pendingRequest) {
                    pendingRequest.abort();
                    pendingRequest = null;
                    view.removeAttribute("aria-busy");
                }
                showMessage("");
                return;
            }
            loadView(path, true, false);
        };
    }

    window.addEventListener("popstate", function () {
        loadView(window.location.pathname, false, false);
    });

    // Refresh only weather content: replacing the document would end fullscreen.
    window.setInterval(function () {
        if (view.getAttribute("data-view") === "weather" && !pendingRequest) {
            loadView("/", false, true);
        }
    }, 600000);
}());
