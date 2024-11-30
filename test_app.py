import pytest
from app import app, db, Usuario
from werkzeug.security import generate_password_hash


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