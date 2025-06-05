// static/prediction_scripts.js
document.addEventListener('DOMContentLoaded', function () {
    const loadOtherCoursesBtn = document.getElementById('loadOtherCoursesBtn');
    const areaSelector = document.getElementById('areaSelector');
    const otherCoursesDisplay = document.getElementById('otherCoursesDisplay');
    const otherCoursesList = document.getElementById('otherCoursesList');
    const otherCoursesTitle = document.getElementById('otherCoursesTitle');
    const noOtherCoursesMessage = document.getElementById('noOtherCoursesMessage');
    const loadingOtherCourses = document.getElementById('loadingOtherCourses');

    // Event listener para carregar outros cursos
    if (loadOtherCoursesBtn && areaSelector && otherCoursesDisplay && otherCoursesList && otherCoursesTitle && noOtherCoursesMessage && loadingOtherCourses) {
        loadOtherCoursesBtn.onclick = function () {
            const selectedArea = areaSelector.value;
            const selectedAreaText = areaSelector.options[areaSelector.selectedIndex].text;

            if (!selectedArea) {
                alert('Por favor, selecione uma área.');
                return;
            }

            // Prepara a UI para carregar
            otherCoursesList.innerHTML = '';
            otherCoursesTitle.textContent = '';
            noOtherCoursesMessage.style.display = 'none';
            loadingOtherCourses.style.display = 'block';
            otherCoursesDisplay.style.display = 'block';

            // Faz a requisição para a API Flask
            fetch(`/api/courses/${selectedArea}`)
                .then(response => {
                    if (!response.ok) {
                        return response.json().then(errData => {
                            throw new Error(errData.error || `Erro HTTP: ${response.status} ${response.statusText}`);
                        }).catch(() => {
                            throw new Error(`Erro HTTP: ${response.status} ${response.statusText}`);
                        });
                    }
                    return response.json();
                })
                .then(data => {
                    loadingOtherCourses.style.display = 'none';
                    otherCoursesTitle.textContent = `Cursos de ${selectedAreaText}`;

                    if (data && Array.isArray(data) && data.length > 0) {
                        // AQUI É A CHAVE: usar displayOtherCourses para criar os elementos corretamente
                        displayOtherCourses(data);
                    } else {
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
            return unsafe;
        }
        return unsafe
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/'/g, "&#x27;");
    }


    // Função para lidar com o clique no curso (ÚNICA VERSÃO)
    function handleCourseClick(event) {
        const courseItem = event.currentTarget;
        const description = courseItem.querySelector('p');

        if (description) {
            // Toggle da descrição
            if (description.style.display === 'none' || description.style.display === '') {
                // Mostra a descrição
                description.style.display = 'block';
                description.style.marginTop = '10px';
                description.style.padding = '10px';
                description.style.backgroundColor = '#f9f9f9';
                description.style.borderLeft = '3px solid #007bff';
                description.style.borderRadius = '4px';
                description.style.animation = 'fadeIn 0.3s ease-in';

                // Adiciona ícone de "expandido"
                const title = courseItem.querySelector('h4');
                if (title && !title.textContent.includes('▼')) {
                    title.textContent = title.textContent.replace('▶', '') + ' ▼';
                }
            } else {
                // Oculta a descrição
                description.style.display = 'none';

                // Adiciona ícone de "fechado"
                const title = courseItem.querySelector('h4');
                if (title) {
                    title.textContent = title.textContent.replace('▼', '') + ' ▶';
                }
            }
        }
    }

    // Função para adicionar evento de clique aos cursos
    function addClickEventsToCourses() {
        const courseItems = document.querySelectorAll('.course-item');

        courseItems.forEach(item => {
            // Remove listeners antigos para evitar duplicação
            item.removeEventListener('click', handleCourseClick);
            // Adiciona o novo listener
            item.addEventListener('click', handleCourseClick);

            // Adiciona estilo visual para indicar que é clicável
            item.style.cursor = 'pointer';
            item.style.transition = 'all 0.3s ease';

            // Efeitos hover
            item.addEventListener('mouseenter', function () {
                this.style.backgroundColor = '#f0f8ff';
                this.style.transform = 'translateY(-2px)';
                this.style.boxShadow = '0 4px 8px rgba(0,0,0,0.1)';
            });

            item.addEventListener('mouseleave', function () {
                this.style.backgroundColor = '';
                this.style.transform = '';
                this.style.boxShadow = '';
            });
        });
    }

    // Adiciona ícones visuais aos títulos dos cursos
    function addExpandIcons() {
        const courseTitles = document.querySelectorAll('.course-item h4');
        courseTitles.forEach(title => {
            if (!title.textContent.includes('▶') && !title.textContent.includes('▼')) {
                title.textContent = title.textContent + ' ▶';
                title.style.color = '#007bff';
            }
        });
    }

    // Função para exibir os cursos carregados (CORRIGIDA)
    function displayOtherCourses(courses) {
        otherCoursesList.innerHTML = '';

        courses.forEach(course => {
            const li = document.createElement('li');
            li.className = 'course-item';
            li.innerHTML = `
                <h4>${escapeHtml(course.nome)}</h4>
                <p style="display: none;">${escapeHtml(course.descricao)}</p>
            `;
            otherCoursesList.appendChild(li);
        });

        // IMPORTANTE: Adiciona eventos de clique aos novos cursos
        addClickEventsToCourses();
        addExpandIcons();
    }


    // Inicializa os eventos para cursos já carregados na página
    addClickEventsToCourses();
    addExpandIcons();


});

// CSS adicional via JavaScript
const style = document.createElement('style');
style.textContent = `
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(-10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .course-item {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 10px;
        background: white;
        transition: all 0.3s ease;
    }
    
    .course-item:hover {
        border-color: #007bff;
        box-shadow: 0 2px 8px rgba(0,123,255,0.2);
    }
    
    .course-item h4 {
        margin: 0 0 5px 0;
        color: #007bff;
        font-size: 1.1em;
    }
    
    .course-item p {
        margin: 0;
        color: #666;
        line-height: 1.5;
    }
    
    .loading-message {
        color: #666;
        font-style: italic;
        text-align: center;
        padding: 20px;
    }
`;
document.head.appendChild(style);