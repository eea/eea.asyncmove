/* global jQuery */

jQuery(document).ready(function($) {
  var async_paste = $("#plone-contentmenu-actions-paste_async");
  async_paste.prepOverlay({
    subtype: 'ajax',
    formselector: 'form',
    filter: '.portalMessage,#content',
    cssclass: 'eea-paste-confirmation-overlay'
  });
  
  // workaround to remove error message upon visiting folder_rename_form
  // which triggers a validation error 
  var hide_error = function(el) {
    var $el = $(el);
    var $error = $el.find('.error');
    var $dd = $error.find('dd');
    if ($error.length) {
      if ($dd.text() === 'You must provide content names') {
        $error.remove();
      }
    }
  };
  hide_error($("#region-content"));
  
  // original rename form from overlay needs to have the orig_template
  // input otherwise it will redirect to folder_contents
  var modify_orig_template = function(el) {
    var $el = $(el);
    var $input = $("<input />", {
      type: 'hidden',
      value: 'async_move',
      name: 'orig_template'
    });
    $input.appendTo($el.find(".formControls"));
  } 
  // set orig_template for rename_confirmation for to asyn_move in order
  // to enforce consistent behaviour as async or normal paste goes to
  // async_move page 
  $("#rename_confirmation").find("input[name='orig_template']").attr('value', 'async_move')
  
  var modify_original_rename = function(el) {
    hide_error(el);
    modify_orig_template(el);
  }
  
  var async_rename = $("#plone-contentmenu-actions-rename_async");
  async_rename.prepOverlay({
    subtype: 'ajax',
    formselector: 'form',
    filter: '.portalMessage,#content',
    cssclass: 'eea-rename-confirmation-overlay',
    closeselector: '[name="form.button.Cancel"]',
    width:'40%',
    afterpost: modify_original_rename
  });

  // workaround to set action for normal rename to folder_rename_form
  $("body").on('click', 'input[name="form.button.rename"]', function(){
    var $el = $(this);
    var $rename_form = $el.closest('form');
    $rename_form.attr('action', 'folder_rename_form');
  });
  
});
