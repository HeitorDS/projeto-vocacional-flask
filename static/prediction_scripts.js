// static/prediction_scripts.js
document.addEventListener('DOMContentLoaded', function() {
    const loadOtherCoursesBtn = document.getElementById('loadOtherCoursesBtn');
    const areaSelector = document.getElementById('areaSelector');
    const otherCoursesDisplay = document.getElementById('otherCoursesDisplay'); // A div que contém a lista e o título
    const otherCoursesList = document.getElementById('otherCoursesList');     // A <ul>
    const otherCoursesTitle = document.getElementById('otherCoursesTitle');   // O <h3>
    const noOtherCoursesMessage = document.getElementById('noOtherCoursesMessage');
    const loadingOtherCourses = document.getElementById('loadingOtherCourses');

    if (loadOtherCoursesBtn && areaSelector && otherCoursesDisplay && otherCoursesList && otherCoursesTitle && noOtherCoursesMessage && loadingOtherCourses) {
        loadOtherCoursesBtn.onclick = function() {
            const selectedArea = areaSelector.value;
            const selectedAreaText = areaSelector.options[areaSelector.selectedIndex].text; // Pega o texto da opção selecionada

            if (!selectedArea) {
                alert('Por favor, selecione uma área.');
                return;
            }

            // Prepara a UI para carregar
            otherCoursesList.innerHTML = ''; // Limpa cursos anteriores
            otherCoursesTitle.textContent = ''; // Limpa título anterior
            noOtherCoursesMessage.style.display = 'none';
            loadingOtherCourses.style.display = 'block'; // Mostra mensagem de carregando
            otherCoursesDisplay.style.display = 'block'; // Garante que a seção de outros cursos esteja visível

            // Faz a requisição para a API Flask
            fetch(`/api/courses/${selectedArea}`) // A rota no Flask espera o valor da option (TI, Saúde, Gestão)
                .then(response => {
                    if (!response.ok) {
                        // Tenta ler o corpo do erro se possível, senão usa o statusText
                        return response.json().then(errData => {
                            throw new Error(errData.error || `Erro HTTP: ${response.status} ${response.statusText}`);
                        }).catch(() => { // Se o corpo não for JSON ou der outro erro
                            throw new Error(`Erro HTTP: ${response.status} ${response.statusText}`);
                        });
                    }
                    return response.json();
                })
                .then(data => {
                    loadingOtherCourses.style.display = 'none';
                    otherCoursesTitle.textContent = `Cursos de ${selectedAreaText}`; // Usa o texto da opção para o título

                    if (data && Array.isArray(data) && data.length > 0) {
                        data.forEach(course => {
                            const listItem = document.createElement('li');
                            listItem.classList.add('course-item');
                            listItem.innerHTML = `<h4>${escapeHtml(course.nome)}</h4><p>${escapeHtml(course.descricao)}</p>`;
                            otherCoursesList.appendChild(listItem);
                        });
                    } else {
                        // Se 'data' não for um array ou estiver vazio, ou se 'data.error' foi tratado no catch
                        noOtherCoursesMessage.textContent = 'Nenhum curso encontrado para esta área ou erro ao buscar dados.';
                        noOtherCoursesMessage.style.display = 'block';
                    }
                })
                .catch(error => {
                    loadingOtherCourses.style.display = 'none';
                    console.error('Erro ao buscar cursos:', error);
                    otherCoursesTitle.textContent = `Cursos de ${selectedAreaText}`;
                    noOtherCoursesMessage.textContent = `Ocorreu um erro: ${error.message}. Tente novamente.`;
                    noOtherCoursesMessage.style.display = 'block';
                });
        };
    } else {
        console.warn("Um ou mais elementos para carregar outros cursos não foram encontrados no DOM.");
    }

    // Função simples para escapar HTML e prevenir XSS básico
    function escapeHtml(unsafe) {
        if (typeof unsafe !== 'string') {
            return unsafe; // Retorna se não for string
        }
        return unsafe
            .replace(/&/g, "&")
            .replace(/</g, "<")
            .replace(/>/g, ">")
            .replace(/'/g, "'");
    }
});