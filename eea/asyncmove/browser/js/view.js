/* global jQuery */

jQuery(document).ready(function($){

  var links = jQuery('body').find('a[href$="async_move_confirmation"]');

  links.prepOverlay({
    subtype: 'ajax',
    formselector: 'form',
    filter: '#content',
    cssclass: 'eea-paste-confirmation-overlay'
  });

});
