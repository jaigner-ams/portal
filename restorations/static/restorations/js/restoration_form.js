(function () {
    'use strict';

    // All extra field names — must match EXTRA_FIELD_CHOICES keys in models.py
    var ALL_EXTRA_FIELDS = [
        'add_blocker', 'stain_and_glaze', 'design_service',
        'include_tibase', 'assembled_bonded',
        'implant_type', 'implant_size', 'tibase_type',
        'number_of_units', 'is_screw_retained',
        'bar_details',
        'model_type', 'arches', 'size',
        'extra_separate_dies', 'vertex_articulator',
        'model_unit_details',
        'gold_anodizing'
    ];

    // Active notes per selection key. Updated as the user picks values; rendered
    // into the #restoration-notes panel. Empty string means "no note for that key."
    var notes = {restoration_type: '', material: '', product: ''};
    // Cached option lists so we can look up a note for the currently selected id
    // without an extra round-trip.
    var lastMaterials = [];
    var lastProducts = [];

    function lookupNote(arr, id) {
        for (var i = 0; i < arr.length; i++) {
            if (String(arr[i].id) === String(id)) {
                return arr[i].display_note || '';
            }
        }
        return '';
    }

    function renderNotes() {
        var panel = document.getElementById('restoration-notes');
        var list  = document.getElementById('restoration-notes-list');
        if (!panel || !list) return;
        var active = [];
        ['restoration_type', 'material', 'product'].forEach(function (k) {
            if (notes[k] && notes[k].trim()) active.push(notes[k]);
        });
        list.innerHTML = '';
        if (active.length === 0) {
            panel.classList.add('hidden');
            return;
        }
        active.forEach(function (text, idx) {
            var p = document.createElement('p');
            if (idx > 0) p.className = 'mt-2';
            p.textContent = text;
            list.appendChild(p);
        });
        panel.classList.remove('hidden');
    }

    function updateSelect(selectId, options, preserveValue) {
        var select = document.getElementById(selectId);
        if (!select) return;
        select.innerHTML = '<option value="">---------</option>';
        options.forEach(function (opt) {
            var option = document.createElement('option');
            option.value = opt.id;
            option.textContent = opt.name;
            if (String(opt.id) === String(preserveValue)) {
                option.selected = true;
            }
            select.appendChild(option);
        });
    }

    function clearSelect(selectId) {
        var select = document.getElementById(selectId);
        if (select) select.innerHTML = '<option value="">---------</option>';
    }

    function setShadeVisible(visible) {
        var row = document.querySelector('.field-shade');
        if (!row) return;
        row.style.display = visible ? '' : 'none';
        if (!visible) {
            var select = document.getElementById('id_shade');
            if (select) select.value = '';
        }
    }

    function setToothNumberVisible(visible) {
        var row = document.querySelector('.field-tooth_number');
        if (!row) return;
        row.style.display = visible ? '' : 'none';
        if (!visible) {
            var input = document.getElementById('id_tooth_number');
            if (input) input.value = '';
        }
    }

    // Show/hide extra field rows based on the visible list.
    // Hidden fields have their values cleared.
    function setExtraFieldsVisibility(visibleFields) {
        var visibleSet = {};
        (visibleFields || []).forEach(function (f) { visibleSet[f] = true; });

        ALL_EXTRA_FIELDS.forEach(function (fieldName) {
            var row = document.querySelector('.field-' + fieldName);
            if (!row) return;
            var show = !!visibleSet[fieldName];
            row.style.display = show ? '' : 'none';

            if (!show) {
                // Clear hidden field values
                var input = row.querySelector('input, select, textarea');
                if (input) {
                    if (input.type === 'checkbox') {
                        input.checked = false;
                    } else {
                        input.value = '';
                    }
                }
            }
        });
    }

    // Restoration type changed: update materials, tooth number, shade, extra fields.
    function onRestorationTypeChange(restorationTypeId) {
        clearSelect('id_material');
        clearSelect('id_product');
        notes.restoration_type = '';
        notes.material = '';
        notes.product = '';
        lastMaterials = [];
        lastProducts = [];

        if (!restorationTypeId) {
            setToothNumberVisible(true);
            setShadeVisible(false);
            setProductVisible(false);
            setExtraFieldsVisibility([]);
            renderNotes();
            return;
        }

        fetch('/restorations/api/options/?restoration_type=' + encodeURIComponent(restorationTypeId), {
            headers: {'X-Requested-With': 'XMLHttpRequest'},
        })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                updateSelect('id_material', data.materials, null);
                setToothNumberVisible(data.requires_tooth_number);
                setShadeVisible(data.requires_shade);
                setProductVisible(false);
                setExtraFieldsVisibility(data.extra_fields || []);
                notes.restoration_type = data.display_note || '';
                lastMaterials = data.materials || [];
                renderNotes();
            });
    }

    function setProductVisible(visible) {
        var row = document.querySelector('.field-product');
        if (!row) return;
        row.style.display = visible ? '' : 'none';
        if (!visible) {
            var select = document.getElementById('id_product');
            if (select) select.value = '';
        }
    }

    // Material changed: update products and show/hide product row.
    function onMaterialChange(materialId, preserveProduct) {
        clearSelect('id_product');
        notes.material = lookupNote(lastMaterials, materialId);
        notes.product = '';
        lastProducts = [];

        if (!materialId) {
            setProductVisible(false);
            renderNotes();
            return;
        }

        fetch('/restorations/api/products/?material=' + encodeURIComponent(materialId), {
            headers: {'X-Requested-With': 'XMLHttpRequest'},
        })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                setProductVisible(data.has_products);
                if (data.has_products) {
                    updateSelect('id_product', data.products, preserveProduct || null);
                }
                lastProducts = data.products || [];
                if (preserveProduct) {
                    notes.product = lookupNote(lastProducts, preserveProduct);
                }
                renderNotes();
            });
    }

    // Product changed: update product note.
    function onProductChange(productId) {
        notes.product = lookupNote(lastProducts, productId);
        renderNotes();
    }

    // Implant type changed: cascade to implant sizes.
    function onImplantTypeChange(implantTypeId, preserveSize) {
        clearSelect('id_implant_size');

        if (!implantTypeId) {
            return;
        }

        fetch('/restorations/api/implant-sizes/?implant_type=' + encodeURIComponent(implantTypeId), {
            headers: {'X-Requested-With': 'XMLHttpRequest'},
        })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                updateSelect('id_implant_size', data.sizes, preserveSize || null);
            });
    }

    document.addEventListener('DOMContentLoaded', function () {
        var typeSelect = document.getElementById('id_restoration_type');
        var materialSelect = document.getElementById('id_material');
        var productSelect = document.getElementById('id_product');
        var implantTypeSelect = document.getElementById('id_implant_type');
        if (!typeSelect) return;

        typeSelect.addEventListener('change', function () {
            onRestorationTypeChange(this.value);
        });

        if (materialSelect) {
            materialSelect.addEventListener('change', function () {
                onMaterialChange(this.value, null);
            });
        }

        if (productSelect) {
            productSelect.addEventListener('change', function () {
                onProductChange(this.value);
            });
        }

        if (implantTypeSelect) {
            implantTypeSelect.addEventListener('change', function () {
                onImplantTypeChange(this.value, null);
            });
        }

        if (!typeSelect.value) {
            // New record: blank everything, hide all extra fields
            clearSelect('id_material');
            clearSelect('id_product');
            setProductVisible(false);
            setShadeVisible(false);
            setExtraFieldsVisibility([]);
        } else {
            // Re-rendered after a validation error: restore visibility/state
            var currentMaterial = materialSelect ? materialSelect.value : null;
            var currentProduct = document.getElementById('id_product');
            currentProduct = currentProduct ? currentProduct.value : null;
            var currentImplantSize = document.getElementById('id_implant_size');
            currentImplantSize = currentImplantSize ? currentImplantSize.value : null;

            fetch('/restorations/api/options/?restoration_type=' + encodeURIComponent(typeSelect.value), {
                headers: {'X-Requested-With': 'XMLHttpRequest'},
            })
                .then(function (r) { return r.json(); })
                .then(function (data) {
                    setToothNumberVisible(data.requires_tooth_number);
                    setShadeVisible(data.requires_shade);
                    setExtraFieldsVisibility(data.extra_fields || []);
                    notes.restoration_type = data.display_note || '';
                    lastMaterials = data.materials || [];
                    // Re-populate materials preserving current selection
                    updateSelect('id_material', data.materials, currentMaterial);
                    // Then fetch products for the current material (which fills
                    // in material+product notes and re-renders).
                    if (currentMaterial) {
                        onMaterialChange(currentMaterial, currentProduct);
                    } else {
                        renderNotes();
                    }
                    // Load implant sizes if implant_type is set
                    if (implantTypeSelect && implantTypeSelect.value) {
                        onImplantTypeChange(implantTypeSelect.value, currentImplantSize);
                    }
                });
        }
    });
})();
