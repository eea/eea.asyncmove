/* global jQuery */

jQuery(document).ready(function() {
  var links = jQuery('body').find('a[href$="paste_confirmation"]');
    links.prepOverlay({
    subtype: 'ajax',
    formselector: 'form',
    filter: '.portalMessage,#content',
    cssclass: 'eea-paste-confirmation-overlay'
  });
});
