odoo.define('pos_aamal.mandatory', function (require) {
    "use strict";

    var screens = require('point_of_sale.screens');
    var gui = require('point_of_sale.gui');
    var core = require('web.core');
    var _t = core._t;
    var Model = require('web.DataModel');
    
    screens.ClientListScreenWidget.include({
       save_client_details: function(partner) {
        var self = this;
        
        var fields = {};
        this.$('.client-details-contents .detail').each(function(idx,el){
            fields[el.name] = el.value || false;
        });

        if (!fields.name) {
            this.gui.show_popup('error',_t('A Customer Name Is Required'));
            return;
        }
        if (!fields.phone) {
            this.gui.show_popup('error',_t('A Customer Phone Is Required'));
            return;
        }
        if (!fields.partner_description) {
            this.gui.show_popup('error',_t('A Customer Product Description Is Required'));
            return;
        }
        
        if (this.uploaded_picture) {
            fields.image = this.uploaded_picture;
        }

        fields.id           = partner.id || false;
        fields.country_id   = fields.country_id || false;

        new Model('res.partner').call('create_from_ui',[fields]).then(function(partner_id){
            self.saved_client_details(partner_id);
        },function(err,event){
            event.preventDefault();
            self.gui.show_popup('error',{
                'title': _t('Error: Could not Save Changes'),
                'body': _t('Your Internet connection is probably down.'),
            });
        });
    } 
    });

});