(function () {
    'use strict';

    // Tooth-number positions as percentages of the chart image. Derived from the
    // number-label groups in tooth_chart.svg (Universal Numbering System), then
    // shifted ~22% toward the chart center so each hotspot sits on the tooth
    // itself rather than on its number in the margin. (Verified by rendering.)
    var TEETH = [
        {n: 1,  l: 16.51, t: 49.33}, {n: 2,  l: 18.11, t: 42.20},
        {n: 3,  l: 17.42, t: 35.36}, {n: 4,  l: 20.72, t: 30.81},
        {n: 5,  l: 21.72, t: 25.74}, {n: 6,  l: 29.01, t: 19.09},
        {n: 7,  l: 33.94, t: 15.14}, {n: 8,  l: 44.80, t: 14.20},
        {n: 9,  l: 53.46, t: 14.86}, {n: 10, l: 63.41, t: 16.63},
        {n: 11, l: 70.98, t: 20.10}, {n: 12, l: 76.49, t: 25.31},
        {n: 13, l: 79.59, t: 30.33}, {n: 14, l: 81.64, t: 36.19},
        {n: 15, l: 83.29, t: 42.45}, {n: 16, l: 83.74, t: 48.86},
        {n: 17, l: 83.35, t: 56.46}, {n: 18, l: 83.20, t: 63.22},
        {n: 19, l: 81.81, t: 70.68}, {n: 20, l: 79.74, t: 75.90},
        {n: 21, l: 74.95, t: 81.06}, {n: 22, l: 68.78, t: 84.58},
        {n: 23, l: 60.49, t: 86.39}, {n: 24, l: 53.73, t: 87.83},
        {n: 25, l: 46.68, t: 88.04}, {n: 26, l: 39.33, t: 87.10},
        {n: 27, l: 32.03, t: 85.06}, {n: 28, l: 26.43, t: 81.29},
        {n: 29, l: 21.91, t: 76.23}, {n: 30, l: 14.82, t: 69.56},
        {n: 31, l: 13.20, t: 61.75}, {n: 32, l: 13.15, t: 55.53}
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
