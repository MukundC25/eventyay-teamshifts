document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('.my-shifts-arrived-btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
      const url = btn.dataset.url
      const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value
      const label = btn.querySelector('.my-shifts-arrived-label')

      fetch(url, {
        method: 'POST',
        headers: {
          'X-CSRFToken': csrfToken,
          'Content-Type': 'application/json',
        },
        credentials: 'same-origin',
      })
        .then(function (resp) {
          if (!resp.ok) {
            return
          }
          return resp.json()
        })
        .then(function (data) {
          if (!data) {
            return
          }
          const icon = btn.querySelector('i')
          if (data.arrived) {
            btn.classList.remove('btn-default')
            btn.classList.add('btn-success')
            icon.classList.remove('fa-circle-o')
            icon.classList.add('fa-check-circle')
            label.textContent = btn.dataset.labelArrived
            btn.title = btn.dataset.labelArrived
          } else {
            btn.classList.remove('btn-success')
            btn.classList.add('btn-default')
            icon.classList.remove('fa-check-circle')
            icon.classList.add('fa-circle-o')
            label.textContent = btn.dataset.labelNotArrived
            btn.title = btn.dataset.labelNotArrived
          }
        })
    })
  })
})
