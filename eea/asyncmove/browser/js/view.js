/* global jQuery */

jQuery(document).ready(function($) {
  var links = jQuery('#edit-bar').find('a');
  var async_paste = links.filter('[href$="async_move_confirmation"]');
  async_paste.prepOverlay({
    subtype: 'ajax',
    formselector: 'form',
    filter: '.portalMessage,#content',
    cssclass: 'eea-paste-confirmation-overlay'
  });

  var async_rename = $("#plone-contentmenu-actions-rename_async");
  async_rename.prepOverlay({
    subtype: 'ajax',
    formselector: 'form',
    filter: '.portalMessage,#content',
    cssclass: 'eea-rename-confirmation-overlay',
    closeselector: '[name="form.button.Cancel"]',
    width:'40%'
  });
});
