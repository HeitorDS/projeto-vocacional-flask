// static/modal_login.js
document.addEventListener('DOMContentLoaded', function() {
    // Pegar o modal
    var modal = document.getElementById("loginModal");

    // Pegar o botão que abre o modal
    var btnOpen = document.getElementById("openLoginModalBtn");

    // Pegar o elemento <span> que fecha o modal
    var btnClose = document.getElementById("closeLoginModalBtn");

    // Quando o usuário clica no botão, abre o modal
    if (btnOpen) {
        btnOpen.onclick = function() {
            if (modal) modal.style.display = "block";
        }
    }

    // Quando o usuário clica no <span> (x), fecha o modal
    if (btnClose) {
        btnClose.onclick = function() {
            if (modal) modal.style.display = "none";
        }
    }

    // Quando o usuário clica fora do modal, fecha-o
    window.onclick = function(event) {
        if (event.target == modal) {
            if (modal) modal.style.display = "none";
        }
    }

    // Opcional: Fechar com a tecla Escape
    document.addEventListener('keydown', function(event) {
        if (event.key === "Escape" || event.key === "Esc") { // "Esc" para navegadores mais antigos
            if (modal && modal.style.display === "block") {
                modal.style.display = "none";
            }
        }
    });
});