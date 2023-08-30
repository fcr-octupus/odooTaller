odoo.define('L10nEC.VATBasesField', function (require) {
"use strict";

var AbstractField = require('web.AbstractField');
var field_registry = require('web.field_registry');
var QWeb = require('web.core').qweb;

var VATBasesField = AbstractField.extend({
    _render: function () {
        var self = this;

        this.$el.html($(QWeb.render('L10nEC.VATBasesField', {
            lines: self.value,
        })));
    },
});

field_registry.add('l10n-ec-vat-bases-field', VATBasesField);

return VATBasesField;

});
