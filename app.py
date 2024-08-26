from flask import Flask, render_template, request, redirect, url_for, session, flash
import requests
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)

app.secret_key = b'\xdc\xc1K\x1a\xf4\x8e+|\t\x8a\xb7l\xb1w\xaf\x82\xdd\x07wa\xb6\x0cH\xf8'

# Configuração da URI do banco de dados MySQL
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:12345@localhost:3306/ecommerce'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # Desativa o rastreamento de modificações, economizando recursos.

db = SQLAlchemy(app)

# Cadastro de Usuário
class Usuario(db.Model):
    email = db.Column(db.String(120), primary_key=True, unique=True, nullable=False)
    username = db.Column(db.String(100), nullable=False)
    senha = db.Column(db.String(200), nullable=False)

# Produto
class Produto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    preco = db.Column(db.Float, nullable=False)
    imagem_url = db.Column(db.String(200), nullable=True)

# Cliente
class Cliente(db.Model):
    id = db.Column(db.String(120), primary_key=True)  # Usando o e-mail como ID
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False, unique=True)

# Pedido
class Pedido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.String(120), db.ForeignKey('cliente.id'), nullable=False)
    total = db.Column(db.Float, nullable=False)
    data_pedido = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())

    cliente = db.relationship('Cliente', backref=db.backref('pedidos', lazy=True))

# Item de Pedido
class ItemPedido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey('pedido.id'), nullable=False)
    produto_id = db.Column(db.Integer, db.ForeignKey('produto.id'), nullable=False)
    quantidade = db.Column(db.Integer, nullable=False)
    preco = db.Column(db.Float, nullable=False)

with app.app_context():
    db.create_all()

# Decorator para exigir login
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            flash('Você precisa estar logado para acessar essa página.')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    try:
        # Faz a requisição à API externa
        response = requests.get('https://fakestoreapi.com/products')
        response.raise_for_status()  # Lança uma exceção se o status code não for 200

        produtos_parceiro = response.json()

        for produto in produtos_parceiro:
            # Verifique se o produto já existe no banco de dados para evitar duplicados
            if not Produto.query.filter_by(nome=produto['title']).first():
                novo_produto = Produto(
                    nome=produto['title'],
                    descricao=produto['description'],
                    preco=float(produto['price']),
                    imagem_url=produto['image']
                )
                db.session.add(novo_produto)
                print(f"Produto '{produto['title']}' adicionado com sucesso.")

        # Comita as mudanças no banco de dados
        db.session.commit()
    
    except requests.exceptions.RequestException as req_err:
        print(f"Erro na requisição: {req_err}")
        flash(f"Erro na requisição à API: {req_err}")
    except Exception as e:
        print(f"Erro ao importar produtos: {e}")
        flash(f'Ocorreu um erro ao importar os produtos: {str(e)}')

    # Após importar os produtos da API, buscar todos os produtos (incluindo os do banco de dados)
    produtos = Produto.query.all()  # Consulta todos os produtos
    return render_template('index.html', produtos=produtos)


@app.route('/adicionar', methods=['GET', 'POST'])
@login_required
def adicionar_produto():
    if request.method == 'POST':
        nome = request.form['nome']
        preco = round(float(request.form['preco']), 2)
        descricao = request.form['descricao']
        estoque = int(request.form['estoque'])

        novo_produto = Produto(nome=nome, preco=preco, descricao=descricao, estoque=estoque)
        db.session.add(novo_produto)
        db.session.commit()

        #flash('Produto adicionado com sucesso!')
        return redirect(url_for('index'))

    return render_template('adicionar_produtos.html')

@app.route('/deletar_produto/<int:produto_id>', methods=['POST'])
@login_required
def deletar_produto(produto_id):
    produto = Produto.query.get(produto_id)
    
    if not produto:
        flash('Produto não encontrado.')
        return redirect(url_for('index'))
    
    db.session.delete(produto)
    db.session.commit()
    flash('Produto deletado com sucesso.')
    
    return redirect(url_for('index'))

@app.route('/editar_produto/<int:produto_id>', methods=['GET', 'POST'])
@login_required
def editar_produto(produto_id):
    produto = Produto.query.get_or_404(produto_id)
    
    if request.method == 'POST':
        produto.nome = request.form['nome']
        produto.preco = float(request.form['preco'])
        produto.descricao = request.form['descricao']
        produto.estoque = int(request.form['estoque'])
        
        db.session.commit()
        
        flash('Produto atualizado com sucesso!')
        return redirect(url_for('index'))

    return render_template('editar_produto.html', produto=produto)





@app.route('/adicionar_ao_carrinho', methods=['POST'])
@login_required
def adicionar_ao_carrinho():
    produto_id = request.form['produto_id']
    produto = Produto.query.get(produto_id)
    
    if not produto:
        return "Produto não encontrado", 404

    if 'carrinho' not in session:
        session['carrinho'] = []

    carrinho = session['carrinho']

    # Verificar se o produto já está no carrinho
    for item in carrinho:
        if item['id'] == produto.id:
            # Garantir que a chave 'quantidade' existe
            item['quantidade'] = item.get('quantidade', 0) + 1
            break
    else:
        # Se o produto não estiver no carrinho, adiciona um novo item
        carrinho.append({
            'id': produto.id,
            'nome': produto.nome,
            'preco': float(produto.preco),  # Certifique-se de que o preço seja um float
            'quantidade': 1
        })
    
    session['carrinho'] = carrinho
    session.modified = True  # Marca a sessão como modificada
    return redirect(url_for('carrinho'))






@app.route('/remover_do_carrinho', methods=['POST'])
@login_required
def remover_do_carrinho():
    produto_id = int(request.form['produto_id'])
    
    if 'carrinho' in session:
        carrinho = session['carrinho']
        for item in carrinho:
            if item['id'] == produto_id:
                carrinho.remove(item)
                break  # Sai do loop após remover o primeiro item correspondente
        session['carrinho'] = carrinho
        session.modified = True  # Marca a sessão como modificada

    return redirect(url_for('carrinho'))

@app.route('/finalizar_compras', methods=['POST'])
@login_required
def finalizar_compras():
    # Receber os dados bancários diretamente do formulário
    numero_cartao = request.form.get('numero_cartao')
    nome_titular = request.form.get('nome_titular')
    validade = request.form.get('validade')
    cvv = request.form.get('cvv')

    # Print para depuração
    print(f"Recebido - Cartão: {numero_cartao}, Titular: {nome_titular}, Validade: {validade}, CVV: {cvv}")

    if not numero_cartao or not nome_titular or not validade or not cvv:
        flash('Por favor, preencha todos os dados bancários.')
        return redirect(url_for('dados_bancarios'))

    # Salvar os dados bancários na sessão
    session['dados_bancarios'] = {
        'numero_cartao': numero_cartao,
        'nome_titular': nome_titular,
        'validade': validade,
        'cvv': cvv
    }

    # Continuar com o processamento da compra
    carrinho = session.get('carrinho', [])
    if not carrinho:
        flash('Seu carrinho está vazio.')
        return redirect(url_for('carrinho'))

    cliente_id = session.get('usuario_id')
    cliente = Cliente.query.filter_by(email=cliente_id).first()

    if not cliente:
        flash('Cliente não encontrado.')
        print("Erro: Cliente não encontrado.")
        return redirect(url_for('index'))

    total = sum([item['preco'] for item in carrinho])

    # Criar um novo pedido
    novo_pedido = Pedido(cliente_id=cliente.id, total=total)
    db.session.add(novo_pedido)
    db.session.commit()

    # Adicionar itens ao pedido
    for item in carrinho:
        novo_item = ItemPedido(
            pedido_id=novo_pedido.id,
            produto_id=item['id'],
            quantidade=1,
            preco=item['preco']
        )
        db.session.add(novo_item)
    db.session.commit()

    # Limpar o carrinho e dados bancários da sessão
    session.pop('carrinho', None)
    session.pop('dados_bancarios', None)
    session.modified = True

    # Redirecionar para a página de confirmação do pedido
    return redirect(url_for('confirmacao_pedido', pedido_id=novo_pedido.id))





@app.route('/confirmacao_pedido/<int:pedido_id>')
@login_required
def confirmacao_pedido(pedido_id):
    pedido = Pedido.query.get_or_404(pedido_id)
    nome_titular = request.args.get('nome_titular')  # Recebendo o nome do titular do URL
    return render_template('finalizar_compras.html', pedido=pedido, nome_titular=nome_titular)



@app.route('/dados_pessoais', methods=['GET', 'POST'])
def dados_pessoais():
    if request.method == 'POST':
        print("Dados recebidos:", request.form)  # Debugging

        nome = request.form.get('nome')
        endereco = request.form.get('endereco')
        cidade = request.form.get('cidade')
        estado = request.form.get('estado')
        cep = request.form.get('cep')

        print(f"Nome: {nome}, Endereço: {endereco}, Cidade: {cidade}, Estado: {estado}, CEP: {cep}")

        if not nome or not endereco or not cidade or not estado or not cep:
            print("Faltando dados no formulário.")
            flash("Por favor, preencha todos os campos.")
            return redirect(url_for('dados_pessoais'))

        # Processar os dados pessoais e endereço
        session['nome'] = nome
        session['endereco'] = endereco
        session['cidade'] = cidade
        session['estado'] = estado
        session['cep'] = cep

        # Redirecionar para a página de dados bancários
        return redirect(url_for('dados_bancarios'))

    return render_template('dados_pessoais.html')

@app.route('/buscar_produtos', methods=['GET'])
def buscar_produtos():
    query = request.args.get('query')
    if query:  # Se houver uma consulta, faça a filtragem
        produtos = Produto.query.filter(Produto.nome.ilike(f'%{query}%')).all()
    else:  # Se o campo de busca estiver vazio, retorne todos os produtos
        produtos = Produto.query.all()
    
    return render_template('index.html', produtos=produtos)



@app.route('/dados_bancarios', methods=['GET', 'POST'])
@login_required
def dados_bancarios():
    if request.method == 'POST':
        # Coletar os dados bancários do formulário
        numero_cartao = request.form.get('numero_cartao')
        nome_titular = request.form.get('nome_titular')
        validade = request.form.get('validade')
        cvv = request.form.get('cvv')

        # Debugging: Verifique se os dados estão sendo recebidos corretamente
        print(f"Recebido - Cartão: {numero_cartao}, Titular: {nome_titular}, Validade: {validade}, CVV: {cvv}")

        # Verificar se todos os campos estão preenchidos
        if not numero_cartao or not nome_titular or not validade or not cvv:
            #flash('Por favor, preencha todos os dados bancários.')
            return redirect(url_for('dados_bancarios'))

        # Salvar os dados bancários na sessão
        session['dados_bancarios'] = {
            'numero_cartao': numero_cartao,
            'nome_titular': nome_titular,
            'validade': validade,
            'cvv': cvv
        }
        session.modified = True

        # Printar os dados bancários para verificação
        print("Dados bancários salvos na sessão:", session['dados_bancarios'])

        # Redirecionar para finalizar a compra
        return redirect(url_for('finalizar_compras'))

    return render_template('dados_bancarios.html')


@app.route('/carrinho')
def carrinho():
    carrinho = session.get('carrinho', [])
    
    # Calcula o total considerando a quantidade de cada item
    total = sum(float(item['preco']) * int(item['quantidade']) for item in carrinho)
    
    return render_template('carrinho.html', carrinho=carrinho, total=total)


@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        senha = request.form['senha']
        senha_hash = generate_password_hash(senha)

        usuario_existente = Usuario.query.filter_by(email=email).first()
        if usuario_existente:
            flash('Email já cadastrado.')
            return redirect(url_for('cadastro'))

        novo_usuario = Usuario(username=username, email=email, senha=senha_hash)
        db.session.add(novo_usuario)

        # Criar também um novo cliente na tabela Cliente
        novo_cliente = Cliente(id=email, nome=username, email=email)
        db.session.add(novo_cliente)

        db.session.commit()

        # Usando o email como identificador na sessão
        session['usuario_id'] = novo_usuario.email
        session['username'] = novo_usuario.username

        return redirect(url_for('login'))
    return render_template('cadastro.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']

        # Debugging prints
        print(f"Email recebido: {email}")
        print(f"Senha recebida: {senha}")

        usuario = Usuario.query.filter_by(email=email).first()

        if usuario:
            print(f"Usuário encontrado: {usuario.username}")
            if check_password_hash(usuario.senha, senha):
                # Usando o email como identificador na sessão
                session['usuario_id'] = usuario.email
                session['username'] = usuario.username
                session['nome_titular'] = usuario.username  # Armazenando o nome do titular na sessão
                #flash('Login realizado com sucesso!')
                print("Login bem-sucedido, redirecionando para index...")
                return redirect(url_for('index'))
            else:
                flash('Senha incorreta.')
                print("Senha incorreta.")
        else:
            flash('Email não encontrado.')
            print("Email não encontrado.")

    return render_template('login.html')



@app.route('/logout', methods=['POST'])
def logout():
    session.clear()  # Limpa todos os dados da sessão
    #flash('Você saiu da sessão com sucesso.')
    return redirect(url_for('index'))  # Redireciona para a página de login



@app.route('/importar_produtos_parceiro')
def importar_produtos_parceiro():
    try:
        print("Fazendo a requisição para a API...")
        response = requests.get('https://fakestoreapi.com/products')
        print(f"Status Code: {response.status_code}")
        response.raise_for_status()  # Lança uma exceção se o status code não for 200

        produtos_parceiro = response.json()
        print(f"Produtos recebidos: {produtos_parceiro}")

        for produto in produtos_parceiro:
            print(f"Verificando se o produto '{produto['title']}' já existe...")
            if not Produto.query.filter_by(nome=produto['title']).first():
                novo_produto = Produto(
                    nome=produto['title'],
                    descricao=produto['description'],
                    preco=float(produto['price']),
                    imagem_url=produto['image']
                )
                db.session.add(novo_produto)
                print(f"Produto '{produto['title']}' adicionado com sucesso.")

        db.session.commit()
        flash('Produtos importados com sucesso!')
    
    except requests.exceptions.RequestException as req_err:
        print(f"Erro na requisição: {req_err}")
        flash(f"Erro na requisição à API: {req_err}")
    except Exception as e:
        print(f"Erro ao importar produtos: {e}")
        flash(f'Ocorreu um erro ao importar os produtos: {str(e)}')
    
    return redirect(url_for('index'))



if __name__ == '__main__':
    app.run(debug=True)
