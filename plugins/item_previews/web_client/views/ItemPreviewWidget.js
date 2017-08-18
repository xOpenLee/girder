import ItemCollection from 'girder/collections/ItemCollection';
import View from 'girder/views/View';
import { restRequest } from 'girder/rest';

import ItemPreviewWidgetTemplate from '../templates/itemPreviewWidget.pug';
import '../stylesheets/itemPreviewWidget.styl';

/**
 * The Item Preview widget shows a preview of items under a given folder.
 * For now, the only supported item previews are image previews.
 */
var ItemPreviewWidget = View.extend({
    events: {
        'click a.g-item-preview-link': function (event) {
            var id = this.$(event.currentTarget).data('id');
            this.parentView.itemListView.trigger('g:itemClicked', this.collection.get(id));
        },
        'click .g-widget-item-previews-wrap': function (event) {
            this.wrapPreviews = !this.wrapPreviews;
            this.render();
            if (this.wrapPreviews) {
                this.$('.g-widget-item-previews-container').addClass('g-wrap');
            } else {
                this.$('.g-widget-item-previews-container').removeClass('g-wrap');
            }
        }
    },

    initialize: function (settings) {
        this.collection = new ItemCollection();

        this.collection.on('g:changed', function () {
            this.trigger('g:changed');
            this.render();
        }, this).fetch({
            folderId: settings.folderId
        });

        this.wrapPreviews = false;
    },

    _MAX_JSON_SIZE: 2e6 /* bytes */,

    _isSupportedItem: function (item) {
        return this._isImageItem(item) || this._isJSONItem(item);
    },

    _isJSONItem: function (item) {
        return /\.(json)$/i.test(item.get('name'));
    },

    _isImageItem: function (item) {
        return /\.(jpg|jpeg|png|gif)$/i.test(item.get('name'));
    },

    render: function () {
        var supportedItems = this.collection.filter(this._isSupportedItem.bind(this));

        this.$el.html(ItemPreviewWidgetTemplate({
            items: supportedItems,
            wrapPreviews: this.wrapPreviews,
            hasMore: this.collection.hasNextPage(),
            isImageItem: this._isImageItem,
            isJSONItem: this._isJSONItem
        }));
        this.enableTooltips();

        // Render any JSON files.
        supportedItems.filter(this._isJSONItem).forEach((item) => {
            var id = item.get('_id');

            // Don't process JSON files that are too big to preview.
            var size = item.get('size');
            if (size > this._MAX_JSON_SIZE) {
                return this.$('.json[data-id="' + id + '"]').text('JSON too big to preview.');
            }

            // Ajax request the JSON files to display them.
            restRequest({
                url: `item/${id}/download`,
                method: 'GET',
                error: null // don't do default error behavior (validation may fail)
            }).done((resp) => {
                this.$('.json[data-id="' + id + '"]').text(JSON.stringify(resp, null, '\t'));
            }).fail((err) => {
                console.error('Could not preview item', err);
            });
        });

        return this;
    }

});

export default ItemPreviewWidget;
