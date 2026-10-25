src
    components
        componentX
            index.jsx
            index.css
    pages
        pageX
            index.jsx
            index.css
    assests
    services
    shared
    store


    em components, todos os componentes que são reutilizados por mais de um componente ou página
    Se houver um componente usado por apenas uma página, deixe ele próximo dessa página

    Assets deve guardar tudo que é  estático, como imagens, vídeos, animações, ícones etc

    services contempla todos os serviços de comunicação externa, com apis ou outras fontes externas

    shared contempla funções reutilizadas pela aplicação, que não tem relação com a renderização em si

    store contempla toda a lógica de gerenciamento de estado global da aplicação, para o compartilhamento de dados entre componentes distintos