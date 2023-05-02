odoo.define("pdf_preview_widget", function (require) {
  "use strict";

  var core = require('web.core');
  var fieldRegistry = require("web.field_registry");
  var basicFields = require("web.basic_fields");

  var PdfPreviewWidget = basicFields.FieldBinaryFile.extend({
    template: "PdfPreviewWidget",
    
    _renderModal: function (data) {
      const self = this;

      if($('.pdf-preview-modal').length) return;

      let modalTemplate = core.qweb.render('PdfPreviewModal', {
        iframe_data: data
      });

      $('body').append(modalTemplate);
      $('.modal-window').addClass('visible');
      $(".modal-close").on('click', function(ev) {
        ev.preventDefault();

        $(this).parent().parent().parent().remove();
      });
    },

    _b64toBlob: function(b64Data, contentType='', sliceSize=512) {
      const byteCharacters = atob(b64Data);
      const byteArrays = [];
    
      for (let offset = 0; offset < byteCharacters.length; offset += sliceSize) {
        const slice = byteCharacters.slice(offset, offset + sliceSize);
    
        const byteNumbers = new Array(slice.length);
        for (let i = 0; i < slice.length; i++) {
          byteNumbers[i] = slice.charCodeAt(i);
        }
    
        const byteArray = new Uint8Array(byteNumbers);
        byteArrays.push(byteArray);
      }
    
      const blob = new Blob(byteArrays, {type: contentType, title: 'Download.pdf'});
      return blob;
    },

    _render: function () {
      const self = this;

      this.$(".oe_field_pdf_preview").on('click', function(ev) {
        ev.preventDefault();

        const resBlob = self._b64toBlob(self.value, 'application/pdf');
        const resFile = new File([resBlob], 'Download.pdf', {type: 'application/pdf'});
        const resUrl = URL.createObjectURL(resFile, {type: 'application/pdf'});

        self._renderModal(resUrl);
      });
    }
  });

  fieldRegistry.add("pdf_preview", PdfPreviewWidget);
});
