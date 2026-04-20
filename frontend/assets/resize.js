(function () {
    function initResizer() {
        var resizer = document.getElementById('sidebar-resizer');
        var sidebar = document.getElementById('sidebar');
        if (!resizer || !sidebar) {
            setTimeout(initResizer, 100);
            return;
        }

        var isResizing = false;

        resizer.addEventListener('mousedown', function (e) {
            isResizing = true;
            resizer.classList.add('resizing');
            document.body.style.cursor = 'col-resize';
            document.body.style.userSelect = 'none';
            e.preventDefault();
        });

        document.addEventListener('mousemove', function (e) {
            if (!isResizing) return;
            var newWidth = Math.max(200, Math.min(520, e.clientX));
            sidebar.style.width = newWidth + 'px';
        });

        document.addEventListener('mouseup', function () {
            if (!isResizing) return;
            isResizing = false;
            resizer.classList.remove('resizing');
            document.body.style.cursor = '';
            document.body.style.userSelect = '';
        });
    }

    initResizer();
})();
