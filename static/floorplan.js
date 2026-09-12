(function () {
    window.initializeFloorplan = function (view) {
        if (view.getAttribute('data-view') !== 'floorplan') { return function () {}; }
        var map = view.querySelector('#fp-map');
        var groups = view.querySelectorAll('.fp-sensor');
        var sensors = [], byId = {}, selected = null, showAll = false, enlarged = false;
        var stopped = false, request = null, timer = null, lastReceived = 0, stale = true;
        var summary = view.querySelector('#fp-summary');
        var connection = view.querySelector('#fp-connection');
        var detail = view.querySelector('#fp-detail');
        var zoom = view.querySelector('#fp-zoom');
        var filter = view.querySelector('#fp-filter');
        var lastSuccess = null;

        function stateLabel(state) { return state === 'open' ? 'Open' : state === 'closed' ? 'Closed' : 'Unavailable'; }
        function changedText(sensor) {
            if (sensor.state === 'unavailable' || !sensor.changed) { return stateLabel(sensor.state); }
            var date = new Date(sensor.changed);
            return stateLabel(sensor.state) + (isNaN(date.getTime()) ? '' : ' since ' + date.toLocaleString());
        }
        function updateDetail() {
            if (!selected) { return; }
            detail.textContent = '';
            var title = document.createElement('strong');
            title.textContent = selected.id + '. ' + selected.name;
            detail.appendChild(title);
            detail.appendChild(document.createTextNode(changedText(selected)));
        }
        function sizes() {
            var box = map.viewBox.baseVal;
            var rect = map.getBoundingClientRect();
            var scale = Math.min(rect.width / box.width, rect.height / box.height);
            if (!scale) { return; }
            sensors.forEach(function (s) {
                var active = selected === s;
                var radius = s.state === 'closed' ? (active ? 8 : 5) : (s.state === 'open' ? 13 : 10);
                s.group.querySelector('.fp-ring').setAttribute('r', radius / scale);
                s.group.querySelector('.fp-hit').setAttribute('r', 22 / scale);
                s.group.querySelector('.fp-halo').setAttribute('r', 18 / scale);
                s.group.querySelector('.fp-anchor').setAttribute('r', 3 / scale);
                s.symbol.setAttribute('font-size', 17 / scale);
            });
        }
        function frame(sensor) {
            var x = Number(sensor.group.getAttribute('data-x'));
            var y = Number(sensor.group.getAttribute('data-y'));
            map.setAttribute('viewBox', [Math.max(0, Math.min(781, x - 280)), Math.max(0, Math.min(600, y - 215)), 560, 430].join(' '));
            sizes();
        }
        function select(sensor) {
            selected = sensor;
            sensors.forEach(function (s) {
                s.group.setAttribute('data-selected', String(s === sensor));
                s.button.setAttribute('aria-pressed', String(s === sensor));
            });
            zoom.disabled = false;
            if (enlarged) { frame(sensor); } else { sizes(); }
            updateDetail();
        }
        function updateList() {
            var issues = 0;
            sensors.forEach(function (s) {
                if (s.state !== 'closed') { issues += 1; }
                s.button.hidden = !showAll && s.state === 'closed';
                s.button.style.order = s.state === 'open' ? 0 : s.state === 'unavailable' ? 1 : 2;
            });
            view.querySelector('#fp-empty').hidden = showAll || issues !== 0;
            view.querySelector('#fp-list-heading').textContent = showAll ? 'All sensors' : 'Open / unavailable';
            filter.textContent = showAll ? 'Show issues' : 'Show all 17';
            filter.setAttribute('aria-pressed', String(showAll));
        }
        function paint(s, state, changed) {
            var newlyOpen = s.state !== 'open' && state === 'open' && lastReceived && !stale;
            if (s.state !== state) {
                s.group.setAttribute('class', 'fp-sensor' + (newlyOpen ? ' fp-pulse' : ''));
            }
            s.state = state;
            s.changed = changed;
            s.group.setAttribute('data-state', state);
            s.group.setAttribute('aria-label', s.name + ': ' + stateLabel(state));
            s.symbol.textContent = state === 'open' ? '!' : state === 'closed' ? '' : '?';
            s.button.setAttribute('data-state', state);
            s.button.querySelector('.fp-list-symbol').textContent = state === 'open' ? '!' : state === 'closed' ? '✓' : '?';
            s.button.querySelector('.fp-list-state').textContent = stateLabel(state);
        }
        function unavailable(message) {
            stale = true;
            sensors.forEach(function (s) { paint(s, 'unavailable', null); });
            summary.textContent = 'Sensor status unavailable';
            summary.setAttribute('data-status', 'unavailable');
            connection.textContent = message;
            if (lastSuccess) {
                var date = new Date(lastSuccess);
                if (!isNaN(date.getTime())) { connection.textContent += ' Last connected: ' + date.toLocaleTimeString(); }
            }
            updateList(); updateDetail(); sizes();
        }
        function receive(data) {
            if (!data || !Array.isArray(data.sensors)) { throw new Error('Invalid response'); }
            if (data.status !== 'connected') {
                var messages = {
                    not_configured: 'Home Assistant not configured.',
                    authentication_error: 'Home Assistant authentication failed.',
                    configuration_error: 'Home Assistant address is invalid.'
                };
                unavailable(messages[data.status] || 'Home Assistant unavailable. Retrying automatically.');
                return;
            }
            var found = {}, open = 0, unknown = 0;
            data.sensors.forEach(function (row) {
                if (!row || !byId[row.id] || found[row.id] || ['open', 'closed', 'unavailable'].indexOf(row.state) < 0) { throw new Error('Invalid sensor'); }
                found[row.id] = row;
            });
            if (Object.keys(found).length !== sensors.length) { throw new Error('Incomplete response'); }
            sensors.forEach(function (s) {
                var row = found[s.id];
                paint(s, row.state, typeof row.last_changed === 'string' ? row.last_changed : null);
                if (row.state === 'open') { open += 1; }
                if (row.state === 'unavailable') { unknown += 1; }
            });
            lastSuccess = data.last_success;
            lastReceived = Date.now(); stale = false;
            summary.textContent = open || unknown ? open + ' open' + (unknown ? ' · ' + unknown + ' unavailable' : '') : 'All monitored openings closed';
            summary.setAttribute('data-status', open ? 'open' : unknown ? 'unavailable' : 'closed');
            connection.textContent = 'Connected · Updates every few seconds';
            updateList(); updateDetail(); sizes();
        }
        function poll() {
            if (stopped || document.hidden || request) { return; }
            var xhr = new XMLHttpRequest();
            request = xhr;
            xhr.open('GET', '/api/ha/floorplan', true);
            xhr.timeout = 7000;
            xhr.setRequestHeader('Accept', 'application/json');
            function finish(ok) {
                if (stopped || request !== xhr) { return; }
                request = null;
                if (ok) {
                    try { receive(JSON.parse(xhr.responseText)); }
                    catch (error) { unavailable('Sensor data could not be read. Retrying automatically.'); }
                } else { unavailable('Dashboard connection lost. Retrying automatically.'); }
                timer = window.setTimeout(poll, 2000);
            }
            xhr.onload = function () { finish(xhr.status === 200 || xhr.status === 503); };
            xhr.onerror = function () { finish(false); };
            xhr.ontimeout = function () { finish(false); };
            xhr.send();
        }
        for (var i = 0; i < groups.length; i += 1) {
            var group = groups[i];
            var s = {id: Number(group.getAttribute('data-id')), name: group.getAttribute('data-name'), group: group, state: 'unavailable', changed: null};
            s.symbol = group.querySelector('.fp-symbol');
            s.button = view.querySelector('#fp-list-' + s.id);
            sensors.push(s); byId[s.id] = s;
            (function (sensor) {
                sensor.group.onclick = function () { select(sensor); };
                sensor.group.onkeydown = function (event) {
                    if (event.key === 'Enter' || event.key === ' ' || event.keyCode === 13 || event.keyCode === 32) { event.preventDefault(); select(sensor); }
                };
                sensor.button.onclick = function () { select(sensor); };
            }(s));
        }
        zoom.onclick = function () { if (selected) { enlarged = true; frame(selected); } };
        view.querySelector('#fp-whole').onclick = function () { enlarged = false; map.setAttribute('viewBox', '0 0 1341 1030'); sizes(); };
        filter.onclick = function () { showAll = !showAll; updateList(); };
        function visibility() {
            window.clearTimeout(timer);
            if (request) { var old = request; request = null; old.abort(); }
            if (!document.hidden) { unavailable('Refreshing sensor status…'); poll(); }
        }
        document.addEventListener('visibilitychange', visibility);
        window.addEventListener('resize', sizes);
        var watchdog = window.setInterval(function () {
            if (!document.hidden && lastReceived && !stale && Date.now() - lastReceived > 12000) { unavailable('Sensor updates are delayed. Retrying automatically.'); }
        }, 1000);
        sizes(); poll();
        return function () {
            stopped = true;
            window.clearTimeout(timer); window.clearInterval(watchdog);
            document.removeEventListener('visibilitychange', visibility);
            window.removeEventListener('resize', sizes);
            if (request) { request.abort(); request = null; }
        };
    };
}());
