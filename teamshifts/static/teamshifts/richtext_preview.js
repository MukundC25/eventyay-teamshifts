document.addEventListener('DOMContentLoaded', function () {
  function getCsrf(container) {
    var el = (container || document).querySelector('input[name="csrfmiddlewaretoken"]')
    return el ? el.value : ''
  }

  document.querySelectorAll('[data-richtext-preview-tab]').forEach(function (tab) {
    var wrapper = tab.closest('[data-richtext-preview-wrapper]')
    if (!wrapper) return

    var previewUrl = wrapper.getAttribute('data-richtext-preview-url')
    var previewEl = wrapper.querySelector('.richtext-preview')
    var form = wrapper.closest('form')

    if (!previewUrl || !previewEl) return

    function render() {
      var textarea = wrapper.querySelector('textarea[data-tiptap-profile]')
      if (!textarea) return

      var params = new URLSearchParams()
      params.append('content', textarea.value)

      fetch(previewUrl, {
        method: 'POST',
        headers: {
          'X-CSRFToken': getCsrf(form),
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        credentials: 'same-origin',
        body: params,
      })
        .then(function (r) { return r.json() })
        .then(function (data) { previewEl.innerHTML = data.html || '' })
        .catch(function () { previewEl.textContent = gettext ? gettext('Preview could not be loaded.') : 'Preview could not be loaded.' })
    }

    if (window.jQuery) {
      window.jQuery(tab).on('shown.bs.tab', render)
    }
  })

  document.querySelectorAll('[data-email-preview-tab]').forEach(function (tab) {
    var wrapper = tab.closest('[data-email-preview-wrapper]')
    if (!wrapper) return

    var previewUrl = wrapper.getAttribute('data-email-preview-url')
    var blocks = wrapper.querySelectorAll('.mail-preview')
    var form = wrapper.closest('form')

    if (!previewUrl || !blocks.length) return

    function render() {
      var params = new URLSearchParams()
      wrapper.querySelectorAll('textarea').forEach(function (ta) {
        params.append('body', ta.value)
      })

      fetch(previewUrl, {
        method: 'POST',
        headers: {
          'X-CSRFToken': getCsrf(form),
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        credentials: 'same-origin',
        body: params,
      })
        .then(function (r) { return r.json() })
        .then(function (data) {
          var previews = data.previews || {}
          blocks.forEach(function (block) {
            block.innerHTML = previews[block.getAttribute('lang')] || ''
          })
        })
        .catch(function () {
          blocks.forEach(function (block) {
            block.textContent = gettext ? gettext('Preview could not be loaded.') : 'Preview could not be loaded.'
          })
        })
    }

    if (window.jQuery) {
      window.jQuery(tab).on('shown.bs.tab', render)
    }
  })
})
