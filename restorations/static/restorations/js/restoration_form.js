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

        if (!restorationTypeId) {
            setToothNumberVisible(true);
            setShadeVisible(false);
            setProductVisible(false);
            setExtraFieldsVisibility([]);
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

        if (!materialId) {
            setProductVisible(false);
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
            });
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
                    // Re-populate materials preserving current selection
                    updateSelect('id_material', data.materials, currentMaterial);
                    // Then fetch products for the current material
                    if (currentMaterial) {
                        onMaterialChange(currentMaterial, currentProduct);
                    }
                    // Load implant sizes if implant_type is set
                    if (implantTypeSelect && implantTypeSelect.value) {
                        onImplantTypeChange(implantTypeSelect.value, currentImplantSize);
                    }
                });
        }
    });
})();
