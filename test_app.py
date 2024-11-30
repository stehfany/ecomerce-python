import pytest
import requests
from app import app, db, Usuario,Produto
from werkzeug.security import generate_password_hash
from unittest.mock import patch


@pytest.fixture(scope="module")
def test_app():
    """Configura a aplicação Flask para os testes."""
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",  # Usa banco em memória para testes
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
    })

    with app.app_context():
        db.create_all()  # Cria as tabelas no banco de dados para testes
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(test_app):
    """Retorna o cliente de teste para fazer requisições."""
    return test_app.test_client()


@pytest.fixture
def app_context(test_app):
    """Retorna o contexto da aplicação para testes."""
    with test_app.app_context():
        yield


@pytest.fixture
def test_db(app_context):
    """Configura o banco de dados para os testes."""
    db.create_all()
    yield db
    db.drop_all()

@pytest.fixture
def client(test_app):
    """Retorna o cliente de teste para fazer requisições."""
    return test_app.test_client()


def mock_api_response(*args, **kwargs):
    """Simula a resposta da API externa."""
    class MockResponse:
        def __init__(self, json_data, status_code):
            self.json_data = json_data
            self.status_code = status_code

        def json(self):
            return self.json_data

        def raise_for_status(self):
            if self.status_code != 200:
                raise requests.exceptions.HTTPError(f"Status code: {self.status_code}")

    # Simula produtos da API
    return MockResponse([
        {"title": "Produto 1", "description": "Descrição 1", "price": 10.0, "image": "url1"},
        {"title": "Produto 2", "description": "Descrição 2", "price": 20.0, "image": "url2"}
    ], 200)


@patch('requests.get', side_effect=mock_api_response)
def test_index_successful_import(mock_get, client):
    """Teste para verificar o carregamento e importação de produtos."""
    response = client.get("/")
    assert response.status_code == 200
    with app.app_context():
        produtos = Produto.query.all()
        assert len(produtos) == 2
        assert produtos[0].nome == "Produto 1"
        assert produtos[1].nome == "Produto 2"


@patch('requests.get', side_effect=mock_api_response)
def test_index_timeout(mock_get, client):
    """Teste para verificar o tratamento de timeout da API."""
    mock_get.side_effect = requests.exceptions.Timeout
    response = client.get("/")
    assert response.status_code == 200
    assert "A requisição à API demorou demais e foi cancelada. Tente novamente mais tarde." in response.data.decode('utf-8')


@patch('requests.get', side_effect=mock_api_response)
def test_index_database_error(mock_get, client):
    """Teste para simular erro no banco de dados."""
    with patch.object(db.session, 'add', side_effect=Exception("Erro no banco de dados")):
        response = client.get("/")
        assert response.status_code == 200
        assert b"Erro inesperado ao processar o produto" in response.data


@patch('requests.get', side_effect=mock_api_response)
def test_index_empty_products(mock_get, client):
    """Teste para quando não houver produtos no banco de dados."""
    with app.app_context():
        db.session.query(Produto).delete()
        db.session.commit()

    response = client.get("/")
    assert response.status_code == 200
    assert b"Produtos" in response.data


def test_cadastro_usuario(client, test_db):
    """Teste para cadastro de usuário."""
    response = client.post("/cadastro", data={
        "username": "teste",
        "email": "teste@teste.com",
        "senha": "senha123"
    })
    assert response.status_code == 302  # Redireciona para outra página
    assert b"Cadastro realizado com sucesso!" in response.data


def test_login_sucesso(client, test_db):
    """Teste para login com sucesso."""
    # Primeiro, cria um usuário no banco
    usuario = Usuario(
        email="usuario@teste.com",
        username="usuario",
        senha=generate_password_hash("senha123")
    )
    with test_db.session.begin():
        test_db.session.add(usuario)

    # Tenta fazer login com o mesmo usuário
    response = client.post("/login", data={
        "email": "usuario@teste.com",
        "senha": "senha123"
    })
    assert response.status_code == 302  # Redireciona para a página principal
    assert b"Login realizado com sucesso!" in response.data


def test_login_senha_incorreta(client, test_db):
    """Teste para login com senha incorreta."""
    # Cria um usuário no banco
    usuario = Usuario(
        email="usuario@teste.com",
        username="usuario",
        senha=generate_password_hash("senha123")
    )
    with test_db.session.begin():
        test_db.session.add(usuario)

    # Tenta fazer login com uma senha errada
    response = client.post("/login", data={
        "email": "usuario@teste.com",
        "senha": "senha_errada"
    })
    assert response.status_code == 200  # Retorna para a página de login
    assert b"Senha incorreta." in response.data


def test_login_email_nao_encontrado(client, test_db):
    """Teste para login com email inexistente."""
    response = client.post("/login", data={
        "email": "nao_existe@teste.com",
        "senha": "qualquer_senha"
    })
    assert response.status_code == 200  # Após redirecionamento, o status deve ser 200
    assert "Email não encontrado." in response.data.decode('utf-8')

def test_adicionar_ao_carrinho(client, add_sample_data):
    """Teste para adicionar um produto ao carrinho."""
    with client.session_transaction() as session:
        session['usuario_id'] = "usuario@teste.com"

    response = client.post("/adicionar_ao_carrinho", data={
        "produto_id": 1,
        "quantidade": 2
    })

    assert response.status_code == 302  # Redireciona para a página do carrinho
    with client.session_transaction() as session:
        assert 'carrinho' in session
        assert len(session['carrinho']) == 1
        assert session['carrinho'][0]['quantidade'] == 2


def test_remover_do_carrinho(client, add_sample_data):
    """Teste para remover um produto do carrinho."""
    with client.session_transaction() as session:
        session['usuario_id'] = "usuario@teste.com"
        session['carrinho'] = [{
            "id": 1,
            "nome": "Produto Teste",
            "preco": 10.0,
            "quantidade": 3
        }]

    response = client.post("/remover_do_carrinho", data={
        "produto_id": 1,
        "quantidade": 2
    })

    assert response.status_code == 302  # Redireciona para a página do carrinho
    with client.session_transaction() as session:
        assert len(session['carrinho']) == 1
        assert session['carrinho'][0]['quantidade'] == 1


def test_finalizar_compras_sem_carrinho(client, add_sample_data):
    """Teste para finalizar compras com o carrinho vazio."""
    with client.session_transaction() as session:
        session['usuario_id'] = "usuario@teste.com"

    response = client.post("/finalizar_compras", data={
        "numero_cartao": "1234567812345678",
        "nome_titular": "Usuario Teste",
        "validade": "12/25",
        "cvv": "123"
    })

    assert response.status_code == 302  # Redireciona para a página do carrinho
    assert "Seu carrinho está vazio." in response.data.decode('utf-8')


def test_finalizar_compras_sucesso(client, add_sample_data):
    """Teste para finalizar compras com sucesso."""
    with client.session_transaction() as session:
        session['usuario_id'] = "usuario@teste.com"
        session['carrinho'] = [{
            "id": 1,
            "nome": "Produto Teste",
            "preco": 10.0,
            "quantidade": 3
        }]

    response = client.post("/finalizar_compras", data={
        "numero_cartao": "1234567812345678",
        "nome_titular": "Usuario Teste",
        "validade": "12/25",
        "cvv": "123"
    })

    assert response.status_code == 302  # Redireciona para a página de confirmação
    with app.app_context():
        from app import Pedido, ItemPedido
        pedido = Pedido.query.first()
        assert pedido is not None
        assert pedido.total == 30.0  # 10.0 x 3

        item = ItemPedido.query.filter_by(pedido_id=pedido.id).first()
        assert item is not None
        assert item.quantidade == 3


def test_buscar_produtos(client, add_sample_data):
    """Teste para buscar produtos."""
    response = client.get("/buscar_produtos?query=Produto")
    assert response.status_code == 200
    assert b"Produto Teste" in response.data

@pytest.fixture
def setup_data():
    """Adiciona dados de teste no banco."""
    with app.app_context():
        usuario = Usuario(email="usuario@teste.com", username="Usuario Teste", senha=generate_password_hash("senha123"))
        produto = Produto(nome="Produto Teste", preco=10.0, descricao="Descrição teste", imagem_url="test.jpg")
        db.session.add(usuario)
        db.session.add(produto)
        db.session.commit()


def test_logout(client, setup_data):
    """Teste para a funcionalidade de logout."""
    with client.session_transaction() as session:
        session['usuario_id'] = "usuario@teste.com"

    response = client.post("/logout")
    assert response.status_code == 302
    assert "Você saiu da sessão com sucesso." in response.data.decode()


def test_dados_pessoais(client):
    """Teste para salvar dados pessoais."""
    response = client.post("/dados_pessoais", data={
        "nome": "Usuario Teste",
        "endereco": "Rua Teste",
        "cidade": "Cidade Teste",
        "estado": "Estado Teste",
        "cep": "12345-678"
    })
    assert response.status_code == 302
    assert "Dados pessoais salvos com sucesso!" in response.data.decode()


def test_dados_bancarios(client):
    """Teste para salvar dados bancários."""
    with client.session_transaction() as session:
        session['usuario_id'] = "usuario@teste.com"

    response = client.post("/dados_bancarios", data={
        "numero_cartao": "1234567812345678",
        "nome_titular": "Usuario Teste",
        "validade": "12/25",
        "cvv": "123"
    })
    assert response.status_code == 302
    assert "Dados bancários salvos com sucesso!" in response.data.decode()




def test_confirmacao_pedido(client, setup_data):
    """Teste para a página de confirmação do pedido."""
    with app.app_context():
        from app import Pedido
        pedido = Pedido(cliente_id="usuario@teste.com", total=30.0)
        db.session.add(pedido)
        db.session.commit()

    with client.session_transaction() as session:
        session['usuario_id'] = "usuario@teste.com"

    response = client.get(f"/confirmacao_pedido/{pedido.id}")
    assert response.status_code == 200
    assert f"Pedido #{pedido.id} Confirmado!" in response.data.decode()