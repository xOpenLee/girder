import _ from 'underscore';
import Backbone from 'backbone';
import 'bootstrap/js/tooltip';

import events from 'girder/events';
import eventStream from 'girder/utilities/EventStream';

var View = Backbone.View.extend({
    constructor: function (opts) { // eslint-disable-line backbone/no-constructor
        if (opts && _.has(opts, 'parentView')) {
            if (opts.parentView) {
                opts.parentView.registerChildView(this);
                this.parentView = opts.parentView;
            }
        } else {
            console.error('View created with no parentView property set. ' +
                          'This view may not be garbage collected.');
        }
        Backbone.View.prototype.constructor.apply(this, arguments);
    },

    /**
     * Remove a view, unbinding its events and removing its listeners on
     * events so that it can be garbage collected.
     */
    destroy: function () {
        _.each(this._childViews, function (child) {
            child.destroy();
        });
        this._childViews = null;

        this.undelegateEvents();
        this.stopListening();
        this.off();
        events.off(null, null, this);
        eventStream.off(null, null, this);

        if (this.parentView) {
            this.parentView.unregisterChildView(this);
        }

        // Modal views need special cleanup.
        if (this.$el.is('.modal')) {
            var el = this.$el;
            if (el.data('bs.modal') && el.data('bs.modal').isShown) {
                el.on('hidden.bs.modal', function () {
                    el.empty().off().removeData();
                }).modal('hide');
                el.modal('removeBackdrop');
            } else {
                el.modal('hideModal');
                el.modal('removeBackdrop');
                el.empty().off().removeData();
            }
        } else {
            this.$el.empty().off().removeData();
        }
    },

    /**
     * It's typically not necessary to call this directly. Instead, instantiate
     * child views with the "parentView" field.
     */
    registerChildView: function (child) {
        this._childViews = this._childViews || [];
        this._childViews.push(child);
    },

    /**
     * Typically, you will not need to call this method directly. Calling
     * destroy on a child element will automatically unregister it from its
     * parent view if the parent view was specified.
     */
    unregisterChildView: function (child) {
        this._childViews = _.without(this._childViews, child);
    },

    /**
     * Apply styled tooltip behavior to elements in this view.
     *
     * Tooltips should be set on HTML elements via the "title" attribute. To force the tooltip to
     * render in a certain orientation, relative to the owning element, the "data-placement"
     * attribute may optionally be set as well. Finally, this method should be called immediately
     * after a view renders its own HTML (via "this.$el.html").
     *
     * @param {Boolean} [dynamic=false] Set to true if tooltips may be inside dynamic elements
     *        (e.g. inside a popover). Default is false, for possibly increased performance. Do not
     *        call this method with both argument values on the same DOM.
     */
    enableTooltips: function (dynamic = false) {
        // This purposely does not take any arguments that affect the style of the template. These
        // should be set on the HTML via data attributes.
        $.fn.tooltip.Constructor.DEFAULTS.placement = 'auto';
        if (dynamic) {
            this.$el.tooltip({
                selector: '[title]',
                container: this.$el
            });
        } else {
            this.$('[title]').tooltip({
                // Setting "container" seems to prevent tooltip jitter near the edges of the screen
                container: this.$el
            });
        }
    }
});

export default View;
