(function () {
    'use strict';

    // Tooth-number positions as percentages of the chart image. Derived from the
    // bounding boxes of the actual tooth artwork in tooth_chart.svg (paths grouped
    // per tooth via the number labels), so each hotspot sits on the tooth itself.
    // (Verified by rendering the overlay.)
    var TEETH = [
        {n: 1,  l: 17.41, t: 47.67}, {n: 2,  l: 18.73, t: 38.91},
        {n: 3,  l: 20.93, t: 31.74}, {n: 4,  l: 23.31, t: 27.22},
        {n: 5,  l: 26.86, t: 20.34}, {n: 6,  l: 31.49, t: 15.94},
        {n: 7,  l: 36.29, t: 12.39}, {n: 8,  l: 44.12, t: 10.49},
        {n: 9,  l: 55.05, t: 10.50}, {n: 10, l: 63.71, t: 12.40},
        {n: 11, l: 70.06, t: 15.95}, {n: 12, l: 73.14, t: 20.35},
        {n: 13, l: 76.69, t: 25.62}, {n: 14, l: 79.07, t: 31.75},
        {n: 15, l: 81.27, t: 38.92}, {n: 16, l: 82.59, t: 46.56},
        {n: 17, l: 82.67, t: 57.09}, {n: 18, l: 82.28, t: 64.87},
        {n: 19, l: 79.52, t: 72.18}, {n: 20, l: 75.77, t: 78.60},
        {n: 21, l: 71.03, t: 83.52}, {n: 22, l: 65.50, t: 86.98},
        {n: 23, l: 61.05, t: 89.05}, {n: 24, l: 53.45, t: 90.22},
        {n: 25, l: 46.55, t: 90.21}, {n: 26, l: 40.22, t: 89.21},
        {n: 27, l: 34.50, t: 87.36}, {n: 28, l: 28.97, t: 83.51},
        {n: 29, l: 24.23, t: 78.59}, {n: 30, l: 20.48, t: 72.17},
        {n: 31, l: 17.72, t: 63.80}, {n: 32, l: 17.33, t: 56.04}
    ];

    document.addEventListener('DOMContentLoaded', function () {
        var modal = document.getElementById('tooth-chart-modal');
        var stage = document.getElementById('tooth-chart-stage');
        var input = document.getElementById('id_tooth_number');
        var openBtn = document.getElementById('open-tooth-chart');
        if (!modal || !stage || !input || !openBtn) return;

        function highlight(value) {
            stage.querySelectorAll('.tooth-hotspot').forEach(function (el) {
                el.classList.toggle('selected', String(el.dataset.tooth) === String(value));
            });
        }

        function openModal() {
            highlight(input.value);
            modal.classList.add('open');
            modal.setAttribute('aria-hidden', 'false');
            document.body.style.overflow = 'hidden';
        }

        function closeModal() {
            modal.classList.remove('open');
            modal.setAttribute('aria-hidden', 'true');
            document.body.style.overflow = '';
        }

        // Build the clickable hotspots over each tooth.
        TEETH.forEach(function (tooth) {
            var b = document.createElement('button');
            b.type = 'button';
            b.className = 'tooth-hotspot';
            b.style.left = tooth.l + '%';
            b.style.top = tooth.t + '%';
            b.dataset.tooth = tooth.n;
            b.title = 'Tooth ' + tooth.n;
            b.setAttribute('aria-label', 'Tooth ' + tooth.n);
            b.addEventListener('click', function () {
                input.value = tooth.n;
                // Notify any listeners (e.g. validation/visibility logic).
                input.dispatchEvent(new Event('change', {bubbles: true}));
                highlight(tooth.n);
                closeModal();
            });
            stage.appendChild(b);
        });

        openBtn.addEventListener('click', openModal);
        modal.querySelectorAll('[data-close]').forEach(function (el) {
            el.addEventListener('click', closeModal);
        });
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' && modal.classList.contains('open')) closeModal();
        });
    });
})();
